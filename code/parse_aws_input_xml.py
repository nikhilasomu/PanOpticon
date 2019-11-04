import re, sys, os, shutil, time, datetime, json
import xml.etree.ElementTree as et
import boto3
from workload import jmeter_script, jmeter_bin, run_workload
from aws_variables import *
import argparse

parser = argparse.ArgumentParser(description='FaaS Benchmarking Tool')
parser.add_argument('input_dir', type=str, help='Input directory')
# parser.add_argument('--no-deploy', dest='toNotDeploy', default=False, action='store_true', help='Option to only test workload incase application is already deployed.')
parser.add_argument('--no-remove', dest='toNotRemove', default=False, action='store_true', help='Option to not remove the application at the end.')
args = parser.parse_args()

# toNotDeploy = args.toNotDeploy
toNotRemove = args.toNotRemove
input_dir = args.input_dir
input_file = sys.argv[1]+"/xml_input.xml"
parser = et.XMLParser(encoding="utf-8")
tree = et.parse(input_file, parser=parser)
root = tree.getroot()

serviceName = root.find('serviceName').text
runtime = root.find('runtime').text
provider = root.find('provider').text
memory = root.find('memory').text
timeout = root.find('timeout').text
region = root.find('region').text
aws_key = root.find('key').text
secret = root.find('secret').text
application = root.find('application')
workload = root.find('workload')
loopCount = workload.find('loopCount').text
noOfUsers = workload.find('noOfUsers').text
rampUpTime = workload.find('rampUpTime').text

print("")
print("-"*100)
print("Memory configuration:", memory, "MB")
print("-"*100)
print("")
functions = []
for function in application:
    functionDict = {}
    functionDict['id'] = function.get('name')
    table_attributes = []
    for functionDetail in function:
        if functionDetail.tag == 'trigger':
            functionDict['triggerType'] = functionDetail.get('type')
            for triggerDetail in functionDetail:
                if triggerDetail.tag == "attribute":
                    table_attribute = {}
                    table_attribute['name'] = triggerDetail.text
                    table_attribute['properties'] = triggerDetail.attrib
                    table_attributes.append(table_attribute)
                    continue
                functionDict[triggerDetail.tag] = triggerDetail.text
            if table_attributes != []:
                functionDict['tableAttributes'] = table_attributes
            continue
        functionDict[functionDetail.tag] = functionDetail.text
    functionDict["environment"] = set()
    functionDict["functionNames"] = []
    functionDict["paths"] = []
    functionDict["topicNames"] = []
    functionDict["queueNames"] = []
    functions.append(functionDict)

newFunctions = functions[:]
iamRoles = ["xray"]
resourcesNeeded = []
tablesNeeded = []
queuesNeeded = []


def getTriggeredByFunction(functionID, functions):
    for pos, function in enumerate(functions):
        if function['id'] == functionID:
            return function, pos

for pos, function in enumerate(functions):
    if function['triggerType'] == 'http':
        triggeredByFunctionID = function['triggeredBy']
        triggeredByFunction, newPosition = getTriggeredByFunction(triggeredByFunctionID, newFunctions)
        triggeredByFunction['environment'].add('HTTP_PATH')
        triggeredByFunction['paths'].append(function['path'])
        item = newFunctions.pop(pos)
        newFunctions.insert(newPosition, item)
    elif function['triggerType'] == 's3':
        if 's3' not in iamRoles:
            iamRoles.append('s3')
    elif function['triggerType'] == 'dynamodb':
        if 'dynamodb' not in iamRoles:
            iamRoles.append('dynamodb')
        if function['tableName'] not in tablesNeeded:
            resource = {}
            resource['type'] = 'dynamodb'
            resource['tableName'] = function['tableName']
            resource['tableAttributes'] = function['tableAttributes']
            resourcesNeeded.append(resource)
            tablesNeeded.append(function['tableName'])
    elif function['triggerType'] == 'sns':
        if 'sns' not in iamRoles:
            iamRoles.append('sns')
        triggeredByFunctionID = function['triggeredBy']
        triggeredByFunction, newPosition = getTriggeredByFunction(triggeredByFunctionID, newFunctions)
        triggeredByFunction['environment'].add('SNS_TOPIC')
        triggeredByFunction['topicNames'].append(function['topicName'])
        item = newFunctions.pop(pos)
        newFunctions.insert(newPosition, item)
    elif function['triggerType'] == 'sqs':
        if 'sqs' not in iamRoles:
            iamRoles.append('sqs')
        triggeredByFunctionID = function['triggeredBy']
        triggeredByFunction, newPosition = getTriggeredByFunction(triggeredByFunctionID, newFunctions)
        triggeredByFunction['environment'].add('SQS_QUEUE')
        triggeredByFunction['queueNames'].append(function['queueName'])
        if function['queueName'] not in queuesNeeded:
            resource = {}
            resource['type'] = 'sqs'
            resource['queueName'] = function['queueName']
            resourcesNeeded.append(resource)
            queuesNeeded.append(function['queueName'])
    elif function['triggerType'] == 'sdk':
        if 'sdk' not in iamRoles:
            iamRoles.append('sdk')
        triggeredByFunctionID = function['triggeredBy']
        triggeredByFunction, newPosition = getTriggeredByFunction(triggeredByFunctionID, newFunctions)
        triggeredByFunction['environment'].add('LAMBDA')
        triggeredByFunction['functionNames'].append(function['handler'])


# writing the serverless.yml file
filecontent = ""
providerDetails = providerDetails.replace("<serviceName>", serviceName)
providerDetails = providerDetails.replace("<providerName>", provider)
providerDetails = providerDetails.replace("<runtime>", runtime)
providerDetails = providerDetails.replace("<memorySize>", memory)
providerDetails = providerDetails.replace("<timeout>", timeout)
providerDetails = providerDetails.replace("<region>", region)

filecontent += providerDetails
filecontent += iamRoleStatementsHeader

for role in iamRoles:
    filecontent += globals()[role+"Permissions"]

filecontent += customVariables

filecontent += resourcesHeader

for resource in resourcesNeeded:
    if resource['type'] == 'dynamodb':
        toWrite = dynamodbResourceFirstHalf.replace("<tableName>", resource['tableName'])
        filecontent += toWrite
        for attribute in resource['tableAttributes']:
            toWrite = dynamodbAttributeTemplate.replace("<attributeName>", attribute['name'])
            toWrite = toWrite.replace("<attributeType>", attribute['properties']['type'])
            filecontent += toWrite
            if "key" in attribute['properties']:
                if attribute['properties']['key'] == 'true':
                    key = attribute['name']
        toWrite = dynamodbKeyAttribute.replace("<attributeName>", key)
        filecontent += toWrite
        filecontent += dynamodbResourceSecondHalf
    elif resource['type'] == 'sqs':
        toWrite = sqsResource.replace("<queueName>", resource['queueName'])
        filecontent += toWrite

filecontent += functionsHeader
for function in newFunctions:
    functionName = function['filename'][:-3]
    toWrite = functionBasicTemplate.replace("<functionName>",functionName)
    toWrite = toWrite.replace("<handlerName>",function['handler'])
    filecontent += toWrite
    if function['triggerType'] != 'sdk':
        filecontent += eventsHeader
    if function['triggerType'] == 'http':
        toWrite = httpEventTemplate.replace("<path>",function['path'])
        toWrite = toWrite.replace("<method>",function['method'])
        filecontent += toWrite
    elif function['triggerType'] == None:
        toWrite = httpEventTemplate.replace("<path>","first")
        toWrite = toWrite.replace("<method>","GET")
        filecontent += toWrite
    elif function['triggerType'] == 's3':
        toWrite = s3EventTemplate.replace("<bucketName>",function['bucketName'])
        filecontent += toWrite
    elif function['triggerType'] == 'dynamodb':
        toWrite = dynamodbEventTemplate.replace("<tableName>",function['tableName'])
        filecontent += toWrite
    elif function['triggerType'] == 'sns':
        toWrite = snsEventTemplate.replace("<topicName>",function['topicName'])
        filecontent += toWrite
    elif function['triggerType'] == 'sqs':
        toWrite = sqsEventTemplate.replace("<queueName>",function['queueName'])
        filecontent += toWrite
    elif function['triggerType'] == 'sdk':
        pass
    # if "environment" in function:
    #     filecontent += environmentVarHeader
    #     if function["environment"] == "HTTP_PATH":
    #         toWrite = HTTP_PATH.replace("<path>",function['path'])
    #         filecontent += toWrite
    #     elif function["environment"] == "SNS_TOPIC":
    #         toWrite = SNS_TOPIC.replace("<topicName>",function['topicName'].title())
    #         filecontent += toWrite
    #     elif function["environment"] == "SQS_QUEUE":
    #         toWrite = SQS_QUEUE.replace("<queueName>",function['queueName'])
    #         filecontent += toWrite
    #     elif function["environment"] == "LAMBDA":
    #         toWrite = LAMBDA.replace("<functionName>",function['functionName'])
    #         filecontent += toWrite

    if function["environment"]:
        filecontent += environmentVarHeader
    for env in function["environment"]:
        if env == "HTTP_PATH":
            for path in function['paths']:
                toWrite = HTTP_PATH.replace("<path>",path)
                filecontent += toWrite
        elif env == "SNS_TOPIC":
            for topic in function['topicNames']:
                toWrite = SNS_TOPIC.replace("<topicName2>",topic.title())
                toWrite = toWrite.replace("<topicName1>", topic)
                filecontent += toWrite
        elif env == "SQS_QUEUE":
            for queue in function['queueNames']:
                toWrite = SQS_QUEUE.replace("<queueName>",queue)
                filecontent += toWrite
        elif env == "LAMBDA":
            for func in function['functionNames']:
                toWrite = LAMBDA.replace("<functionName>",func)
                filecontent += toWrite
 

os.chdir(input_dir)
f = open("serverless.yml","w+")
f.write(filecontent)
f.close()

print("Your application is being deployed...")
output = os.popen('serverless deploy').read()
obj = re.search('(GET) - https://([a-zA-Z0-9-.]*)([/a-zA-Z0-9]*)',output)
try:
    method = obj.group(1)
except:
    print("Serverless deploy ERROR")
    print(output)
    exit()
url = obj.group(2)
path = obj.group(3)
print(url)
print(path)

print("\nJMeter output:")
print("-"*100)
run_workload(url, method, path, loopCount, noOfUsers, rampUpTime)

def get_service_graph(start, end):
    data = xray.get_service_graph(StartTime=start, EndTime=end)
    done = False
    for service in data['Services']:
        done = True
        if service["Type"] != "client":
            print("-"*100)
            print("Name: "+service["Name"])
            print("Type: "+service["Type"])
            print("Total response time(s): ", service["SummaryStatistics"]["TotalResponseTime"])
            print("Total count: ", service["SummaryStatistics"]["TotalCount"])
            if service["SummaryStatistics"]["TotalCount"] != 0:
                avg = service["SummaryStatistics"]["TotalResponseTime"]/service["SummaryStatistics"]["TotalCount"]*1000
                print("Avg(ms): ", avg)
    return done

xray = boto3.client("xray",
    aws_access_key_id=aws_key,
    aws_secret_access_key=secret,
)
gap = datetime.timedelta(minutes=5)
start = datetime.datetime.utcnow()
start_norm = datetime.datetime.now()
os.system(jmeter_bin+"/jmeter -n -t "+jmeter_script+" -l output.csv -e -o output")
end = datetime.datetime.utcnow()
end_norm = datetime.datetime.now()
end = end + gap
end_norm = end_norm + gap

print("\nPolling to get trace data...")

time.sleep(60)
for i in range(4):
    time.sleep(i*60)
    print("Iteration: ", i)
    done = get_service_graph(start, end)
    if done == True:
        break

pattern = r"Duration: (\d*\.*\d*).*Billed Duration: (\d*).*Memory Size: (\d*).*Max Memory Used: (\d*)"

def average(metrics):
    N = float(len(metrics))
    if N == 0.0:
        return (0,0,0,0)
    return (sum(float(t[0]) for t in metrics)/N,
            sum(float(t[1]) for t in metrics)/N,
            sum(float(t[2]) for t in metrics)/N,
            sum(float(t[3]) for t in metrics)/N)

def average_2(metrics):
    N = float(len(metrics))
    if N == 0.0:
        return (0,0,0,0)
    R = len(metrics[0])
    return tuple(sum(float(x[i]) for x in metrics)/N for i in range(R))

print("\nFunction execution metrics")
for function in newFunctions:
    functionName = function['filename'][:-3]
    print("-"*100)
    print(functionName)
    now = datetime.datetime.utcnow()
    duration = now - start
    duration_in_s = duration.total_seconds()
    minutes = divmod(duration_in_s, 60)[0]
    logs = os.popen('serverless logs -f '+functionName+' --startTime '+str(int(minutes)+5)+'m').read()
    metrics = re.findall(pattern, logs)
    avg = average(metrics)
    avg_2 = average_2(metrics)
    print("Duration(ms), Billed Duration(ms), Memory Size(MB), Max Memory Used(MB)")
    print(avg)

if toNotRemove == False:
    os.system('serverless remove')
    os.system('rm -rf output/')
    os.system('rm -f output.csv serverless.yml jmeter.log')