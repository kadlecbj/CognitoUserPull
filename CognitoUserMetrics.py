#!/usr/bin/python3

#Author: Bryan Kadlec June 2023

#TODO: Add IAM functionality for pulling Access Key usage.
#TODO: Add Excel colors for recently used accounts (Last Month/Used/Never Used/Disabled)
#TODO: email automation of sending the file
#TODO: Add an argument for User Pool Name as this currently only works if you have one user pool with multiple groups.

import boto3
from botocore.config import Config
from datetime import datetime
import pandas as pd
import jinja2
import argparse
import openpyxl

parser = argparse.ArgumentParser()

parser.add_argument("-r", "--region", dest="region", required=True, help="AWS Region")
parser.add_argument("-c", "--customer", dest="customer", required=True, help="The customer's name you wish to lookup.")
parser.add_argument("-p", "--profile", dest="awsProfile", default="default", help="The AWS profile you wish to use from your ~/.aws/credentials file.")

args = parser.parse_args()

users = []
userAttr = {}
session = boto3.Session(profile_name=args.awsProfile)

client = session.client('cognito-idp', region_name=args.region)

userPoolList = client.list_user_pools(
    MaxResults=1
)

userPool = userPoolList.get('UserPools')[0].get('Id')

response = client.list_users_in_group(
    UserPoolId=userPool,
    GroupName=args.customer,
)
userList = []
for user in response.get('Users'): 
    userList.append(user.copy())

while 'NextToken' in response:
    response = client.list_users_in_group(
    UserPoolId=userPool,
    GroupName=args.customer,
    NextToken=response.get('NextToken')
    )
    for user in response.get('Users'): 
        userList.append(user.copy())

for user in userList:
    #print(user.get('Username'))
    for attr in user.get('Attributes'):
        if attr.get('Name') == 'email':
            email = attr.get('Value')

    userLastAuth = client.admin_list_user_auth_events(
    UserPoolId=userPool,
    Username=user.get('Username'),
    MaxResults=1
    )
    lastLogin = user.get('UserCreateDate')
    for event in userLastAuth.get('AuthEvents'):
        #print(event)
        if event.get('EventType') == 'SignIn' or event.get('EventType') == 'PasswordChange':
            #print(event.get('EventFeedback'))
            lastLogin =  event.get('CreationDate')
    #print(lastLogin)
    userAttr["Username"] = user.get('Username')
    userAttr["Email"] = email
    userAttr["Created"] = user.get('UserCreateDate').strftime("%m/%d/%Y %H:%M:%S")
    userAttr["Status"] = user.get('UserStatus')
    userAttr["Last Login"] = lastLogin.strftime("%m/%d/%Y %H:%M:%S") #user.get('UserLastModifiedDate')
    userAttr["Enabled"] = user.get('Enabled')
    users.append(userAttr.copy())

df = pd.DataFrame(users)

filename = args.customer + "_aws_logins.xlsx"

columns = df.columns

writer = pd.ExcelWriter(filename)
df.to_excel(writer, index=False, sheet_name="User Logins")
for column in df:
    column_length = max(df[column].astype(str).map(len).max(), len(str(column)))
    col_idx = df.columns.get_loc(column)
    writer.sheets['User Logins'].column_dimensions[chr(65+col_idx)].width = column_length + 2

writer.close()
