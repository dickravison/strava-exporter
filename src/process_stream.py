import boto3
import os
from datetime import datetime, timedelta

def lambda_handler(event, context):
    #Process each record from the stream and if its an activity, take the data and pass it to the update_stats function for the day, week and year.
    for record in event['Records']:
        eventtype = str(record['dynamodb']['Keys']['SK']['S'])
        if eventtype.startswith("ACTIVITY"):
            #Set variables from new record
            user = record['dynamodb']['NewImage']['PK']['S']
            uid = record['dynamodb']['NewImage']['GSI1PK']['S']
            date = record['dynamodb']['NewImage']['GSI1SK']['S']
            activity = record['dynamodb']['NewImage']['activity']['S']
            distance = int(float(record['dynamodb']['NewImage']['distance']['N']))
            movingtime = int(float(record['dynamodb']['NewImage']['moving_time']['N']))
            
            #Convert date from Strava format for use as sort key and also find the start of the week for the activity
            formatdate = datetime.strptime(date,"%Y-%m-%dT%H:%M:%SZ")
            sdate = formatdate - timedelta(days=formatdate.weekday())
            weekstring = sdate.strftime("%Y#%m#%d")
            week = "STATS#" + activity + "#" + weekstring
            
            #Get just UID
            splituid = uid.split('#')[0] + "#STAT"
            
            #Loop through year, month, day and update the stats for each
            for i in range(3):
                y = week.rsplit('#', i)[0]
                z = weekstring.rsplit('#', i)[0]
                update_stats(user, y, distance, movingtime, splituid, z)
        else:
            print("Not an activity")


def update_stats(user, sk, eventDistance, eventTime, gsipk, gsisk):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    
    #Update the statistics using the data being provided from the previous function, if it doesn't already exist then create it.
    table.update_item(
        Key={
            'PK': user,
            'SK': sk
        },
        UpdateExpression=(
            'SET sessions = if_not_exists(sessions, :initial) + :num,'
            'distance = if_not_exists(distance, :initial) + :dist,'
            'moving_time = if_not_exists(moving_time, :initial) + :movingtime,'
            'GSI1PK = :gsi1pk,'
            'GSI1SK = :gsi1sk' 
        ),
        ExpressionAttributeValues={
            ":num": 1,
            ":initial": 0,
            ":dist": eventDistance,
            ":movingtime": eventTime,
            ":gsi1pk": gsipk,
            ":gsi1sk": gsisk
        },
    )