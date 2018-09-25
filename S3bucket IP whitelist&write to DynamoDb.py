import json
import logging
import boto3
import ast

from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


#bucket_name = 'testwaf1234'
whitelistKey = 's3-whitelist-test'
#whiteListIpsAllow= [ "10.123.23.234/24", "10.123.23.226/24"]
whiteListIpsAllow= []
whiteListIpsDeny = [ "10.23.23.24/32" ]
table_name = "WHITELIST_DATA"
table_chk_name = "WHITELIST_DATA_CHK"

def createTableWL():
    try:
        print("Create table and udate..")
        dynamodb_clnt = boto3.client('dynamodb')
        wlchktable = dynamodb_clnt.create_table(
                    TableName=table_chk_name,
                    KeySchema=[
                        {
                            'AttributeName': 'IP',
                             'KeyType': 'HASH'
                            },
                        {
                            'AttributeName': 'BUCKET',
                             'KeyType': 'RANGE'
                            },
                        ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'IP',
                            'AttributeType': 'S',
                            },
                        {
                            'AttributeName': 'BUCKET',
                            'AttributeType': 'S',
                            },

                        ],
                    ProvisionedThroughput={
                            'ReadCapacityUnits': 1,
                            'WriteCapacityUnits': 1
                        }
                )
    except Exception as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("Table already exist, continue")
        else:
            print("Unknown error, exit")
            raise

def addEntryToTable(ip, con_type, bcg_office, bucket_name):
    try:
        dynamodb_clnt = boto3.client('dynamodb')
        response = dynamodb_clnt.put_item(
                TableName=table_chk_name,
                Item={
                    'IP': { "S": ip },
                    'BUCKET': { "S": bucket_name },
                    'BCG_OFFICE': { "S": bcg_office },
                    'CON_TYPE': { "S": con_type }
                    }
                )
    except Exception as e:
        print("Exception from addEntryToTable :: " + str(e))
        raise

def makeWhiteListFromDB(scope_global, wlIP, bucket_name):
    #pass
    if scope_global.strip() == "yes":
        dynamodb = boto3.resource('dynamodb')
        wltable = dynamodb.Table(table_name)
        response = wltable.scan(
            Select='ALL_ATTRIBUTES'
        )

        items = response['Items']
        for item in items:
            print("item['IP']" + item['IP'])
            whiteListIpsAllow.append(item['IP'])
            addEntryToTable(item['IP'], item['CON_TYPE'], item['BCG_OFFICE'], bucket_name)
    else:
        if not wlIP:
            print("Whitelist IP value have ceom from cfn, exting..")
            raise Exception("wlIP did not coe with a value..")
        else:
            whiteListIpsAllow.append(wlIP.strip())

def makepolicy(policy, policyExist):
    #make policy here
    if policyExist is True:
        #make policy form the existing one
        print("policy['Version] : " + policy['Version'])
        print( "policy['Statement'][0]['Principal'] : " + policy['Statement'][0]['Principal'])
        policy['Statement'][0]['Condition'] = {}
        policy['Statement'][0]['Condition']['IpAddress'] = {}
        policy['Statement'][0]['Condition']['IpAddress']['aws:SourceIp'] = whiteListIpsAllow
        policy['Statement'][0]['Condition']['NotIpAddress'] = {}
        policy['Statement'][0]['Condition']['NotIpAddress']['aws:SourceIp'] = whiteListIpsDeny
    else:
        #make new ploicy
        #policy = {}
        policy['Version'] = '2012-10-17'
        policy['Statement'] = []
        policy['Statement'].append({})
        policy['Statement'][0]['Action'] = 's3:GetObject'
        policy['Statement'][0]['Principal'] = '*'
        policy['Statement'][0]['Resource'] = 'arn:aws:s3:::testwaf1234/*'
        policy['Statement'][0]['Effect'] = 'Allow'
        policy['Statement'][0]['Sid'] = 'AddPerm'
        policy['Statement'][0]['Condition'] = {}
        policy['Statement'][0]['Condition']['IpAddress'] = {}
        policy['Statement'][0]['Condition']['IpAddress']['aws:SourceIp'] = whiteListIpsAllow
        policy['Statement'][0]['Condition']['NotIpAddress'] = {}
        policy['Statement'][0]['Condition']['NotIpAddress']['aws:SourceIp'] = whiteListIpsDeny

    return policy

def lambda_handler(event, context):
    # TODO implementa
    s3 = boto3.client('s3')
    print("REQUEST RECEIVED:\n" + json.dumps(event, indent=2))

    bucket_name = event['ResourceProperties']['bucket']
    print("bucket name ::: " + bucket_name)

    #Is it that both scope and IP will come togeather, assuming so
    scope_global = event['ResourceProperties']['global']
    print("scope from lambda ::: " + scope_global)

    wlIP = event['ResourceProperties']['wlIP']
    print("whitelist IP from lambda ::: " + wlIP)

    path = event['ResourceProperties']['path']
    region = event['ResourceProperties']['region']

    #create whitelist table, creates table if table does not exist
    createTableWL()

    #make whitelist from dynamoTable
    makeWhiteListFromDB(scope_global, wlIP, bucket_name)
    #print("WhiteList Ips List :: " + whiteListIpsAllow)

    policy = {}
    policyExist = False
    try:
        #get bucket policy if it has and add the whitelist
        bpolicy = s3.get_bucket_policy(Bucket=bucket_name)
        #print("Existing policy :: " + json.dumps(bpolicy['Policy']))
        policy = ast.literal_eval(bpolicy['Policy'])
        print(policy)
        policyExist=True
    except Exception as e:
        if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
            print("there is not bucket policy, make new one")
        else:
            print("Encountered unknown error... ")
            print("Exception :: " + str(e))
            raise

    #make policy Here
    policyFinal = makepolicy(policy, policyExist)

    #convert dict to json to apply to bucket
    jsonPolicyFinal = json.dumps(policyFinal)
    print(jsonPolicyFinal)

    s3.put_bucket_policy(Bucket='testwaf1234', Policy=jsonPolicyFinal)
    # bucket_policy = {
    #     'Version': '2012-10-17',
    #     'Statement': [{
    #         'Sid': 'AddPerm',
    #         'Effect': 'Allow',
    #         'Principal': '*',
    #         'Action': ['s3:GetObject'],
    #         'Resource': "arn:aws:s3:::%s/*" % bucket_name
    #     }]
    # }

    #bucket_policy = json.dumps(bucket_policy)

    #resp = s3.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy)
    #print("result :: " + str(resp))
    return 0

