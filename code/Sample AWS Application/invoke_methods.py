import boto3
import os
from botocore.vendored import requests
import json
import random
import string
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch

libraries = ('botocore', 'boto3')
patch(libraries)

def random_string_generator(str_size):
    allowed_chars = string.ascii_letters + string.digits
    return ''.join(random.choice(allowed_chars) for x in range(str_size))

def upload_file_to_bucket(fileSize, bucketName):
    #make file based on fileSype
    #calculate overhead
    file_name = "/tmp/log.txt"
    f = open(file_name,"wb+")
    f.seek(fileSize-1)
    f.write(b"\0")
    f.close()
    s3 = boto3.client("s3")
    s3.upload_file(file_name, bucketName, "log.txt")

def insert_into_dynamo_db(tableName):
    dynamodb = boto3.client('dynamodb')
    # maybe create a entry based on schema and insert 
    # entry={'email':{'S':'appln@123'}}
    # dynamodb.put_item(TableName=tableName, Item=entry)
    table = dynamodb.describe_table(TableName=tableName)
    schema = table['Table']['AttributeDefinitions']
    print(schema)
    entry = {}
    for attribute in schema:
        if attribute['AttributeType'] == 'S':
            value = random_string_generator(10)
        elif attribute['AttributeType'] == 'N':
            value = str(random.randint(0,10000))
        entry[attribute['AttributeName']] = {attribute['AttributeType']:value}
    print(entry)
    dynamodb.put_item(TableName=tableName, Item=entry)

def publish_message_sns(topicName, message):
    topicArn = os.environ[topicName]
    client = boto3.client('sns')
    response = client.publish(TargetArn=topicArn,Message=message)
    print(response)

def send_message_sqs(queueName, message):
    queueURL = os.environ[queueName]
    sqs = boto3.client('sqs')
    response = sqs.send_message(QueueUrl=queueURL, MessageBody=message)
    print(response)

def trigger_http_endpoint(path, method, message={}):
    #include other methods if necessary
    httpEndpoint = os.environ[path]
    headers = {
        'content-type': 'application/json',
        "content-length": str(len(message))
    }
    r = requests.post(httpEndpoint, data=json.dumps(message), headers=headers)
    print(r.status_code)

def invoke_lambda(funcName, message):
    functionName = os.environ[funcName]
    lambda_client=boto3.client('lambda')
    # asynchronous invocation
    invoke_response = lambda_client.invoke(FunctionName=functionName,
                                           InvocationType='Event',
                                           Payload=json.dumps(message))
    print("Response from lambda_function2(): "+str(invoke_response))
