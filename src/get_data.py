import requests
import json
import os
import boto3
import botocore
import time
from decimal import Decimal
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

def get_access_token(event, context):
    dynamodb = boto3.resource('dynamodb')
    
    #Get access token from DynamoDB table
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    response = table.get_item(
        Key={
            'PK': 'APP',
            'SK': 'CONFIG'
        }
    )
    items = response['Item']
    client_id = items['client_id']
    client_secret = items['client_secret']
    access_token = items['access_token']
    refresh_token = items['refresh_token']
    expire = int(items['expires_at'])
    seconds = int(time.time())
    #If the access token has expired, refresh the token
    if expire < seconds:
        access_token = refresh_access_token(refresh_token, client_id, client_secret, event['USER'])
    
    getActivities(client_id, client_secret, access_token, event['USER'])

def refresh_access_token(refresh, client_id, client_secret, user):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    
    #Request a new token
    url = 'https://www.strava.com/oauth/token'
    myobj = {'client_id': client_id, 'client_secret': client_secret, 'grant_type': 'refresh_token', 'refresh_token': refresh}
    x = requests.post(url, data = myobj)
    resp = x.json()

    #Get token data and store update it in DynamoDB
    access_token=resp['access_token']
    refresh_token=resp['refresh_token']
    expires=resp['expires_at']

    response = table.put_item(
        Item={
        'PK': 'APP',
        'SK': 'CONFIG',
        'client_id': client_id,
        'client_secret': client_secret,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_at': expires
        }
    )
    return access_token

def getActivities(client_id, client_secret, access_token, user):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    #Get last 200 activities
    header = {'Authorization': 'Bearer ' + access_token}
    url='https://www.strava.com/api/v3/athlete/activities?per_page=200'
    response = requests.get(url, headers = header)
    activities = json.loads(response.text, parse_float=Decimal)

    #Loop over all activities and pull out the data we want, then store it as a new item in DynamoDB
    for x in activities:
        item = {}
        item['PK'] = 'USER#' + user
        item['GSI1PK'] = str(x["athlete"]["id"]) + "#ACTIVITY"
        item['GSI1SK'] = x['start_date']
        item['id'] = x['id']
        item['name'] = x['name']
        item['average_speed'] = x['average_speed']
        item['max_speed'] = x['max_speed']
        item['distance'] = x['distance']
        item['moving_time'] = x['moving_time']
        
        #Loop over fields that may or may not be present
        fields = ['average_heartrate', 'max_heartrate', 'average_cadence', 'average_watts', 'max_watts', 'elev_high', 'elev_low']
        for i in fields:
            if i in x:
                item[i] = x[i]

        #Format the activity type
        if x['type'] in ('VirtualRun', 'Run'):
            item['activity'] = 'RUN'
        elif x['type'] in ('VirtualRide', 'Ride'):
            item['activity'] = 'BIKE'
        elif x['type'] == 'Swim':
            item['activity'] = 'SWIM'
        else:
            item['activity'] = 'IGNORE'

        #If the activity isn't a swim, bike or run, ignore it. Probably should move this to the start of the function
        if item['activity'] in ('SWIM', 'RUN', 'BIKE'):
            #Format sort key
            sdate = datetime.strptime(item['GSI1SK'],"%Y-%m-%dT%H:%M:%SZ")
            startofweek = sdate - timedelta(days=sdate.weekday())
            datestring = startofweek.strftime("#%Y#%m#%d#")
            item['SK'] = 'ACTIVITY#' + item['activity'] + datestring + str(item['id'])
            
            try:
                response = table.put_item(
                    Item=item,
                    ConditionExpression='attribute_not_exists(PK) AND attribute_not_exists(SK)'
                )
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                    raise









