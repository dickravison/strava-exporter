import os
import math
import boto3
from boto3.dynamodb.conditions import Key,Attr
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    
    #Get UID of user
    pk="USER#" + event['USER']
    sk="ATHLETE"
    response = table.query(
        KeyConditionExpression=(Key('PK').eq(pk) & Key('SK').eq(sk)),
    )
    r = response['Items']
    uid = r[0]['GSI1PK'] 
    
    #Get todays date and what weekday it is
    today=datetime.today()
    startOfMonth=today.strftime('%d')
    startOfWeek=today.weekday()
    
    if startOfMonth == "1":
        #Get last month, format it and pass to notify function
        thismonth = int(today.strftime("%m"))
        lastmonth = thismonth - 1
        #Check how many digits are in the month and add a 0 to the start if its required
        digits = int(math.log10(lastmonth)) + 1
        if digits < 2:
            notifysk = today.strftime("%Y#0") + str(lastmonth)
        else:
            notifysk = today.strftime("%Y#") + str(lastmonth)
        notifypk = uid + "#STAT"
        notify(notifypk, notifysk, "Monthly")
    elif startOfWeek == 0:
        #Get start of the week, format it and pass to notify function
        startofweek = today - timedelta(days=7)
        notifysk = startofweek.strftime("%Y#%m#%d")
        notifypk = uid + "#STAT"
        notify(notifypk, notifysk, "Weekly")

def notify(pk, sk, period):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

    #Get users stats for the period defined in the sort key
    response = table.query(
        IndexName="GSI1",
        KeyConditionExpression=(Key('GSI1PK').eq(pk) & Key('GSI1SK').eq(sk)),
    )
    r = response['Items']

    #Set stats to 0
    swimsessions=0
    swimdistance=0
    bikesessions=0
    bikedistance=0
    runsessions=0
    rundistance=0

    #Loop over the query results and build up the local stats variables
    for x in r:
        activity=x['SK']
        y=activity.split('#')[1]
        if y == "SWIM":
            swimsessions = x['sessions']
            swimdistance = x['distance']
        elif y == "BIKE":
            bikesessions = x['sessions']
            bikedistance = x['distance']
        elif y == "RUN":
            runsessions = x['sessions']
            rundistance = x['distance']
            
    #Set totals
    totaldistance = swimdistance + bikedistance + rundistance
    totalsessions = swimsessions + bikesessions + runsessions
    
    #Build summary messages
    swimsummary = "\n\n*Swim*\nDistance covered: " + str(swimdistance/1000) + "km\nNumber of sessions: " + str(swimsessions) 
    bikesummary = "\n\n*Bike*\nDistance covered: " + str(bikedistance/1000) + "km\nNumber of sessions: " + str(bikesessions)
    runsummary = "\n\n*Run*\nDistance covered: " + str(rundistance/1000) + "km\nNumber of sessions: " + str(runsessions)
    total = "\n\n*Total*\nDistance covered: " + str(totaldistance/1000) + "km\nNumber of sessions: " + str(totalsessions)
    
    #Build complete message and pass to telegram function
    message="*" + period + " Training Summary*" + swimsummary + bikesummary + runsummary + total
    
    sns = boto3.client('sns')
    sns.publish(TopicArn=os.environ['SNS_TOPIC'],Message=message)