import re, sys, time, os
from workload import jmeter_script, jmeter_bin, run_workload
from google.cloud import monitoring_v3
from google.cloud.trace_v1.types import Timestamp
from google.cloud.trace_v1 import trace_service_client
import xml.etree.ElementTree as et
from gcf_variables import *
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
project = root.find('project').text
memory = root.find('memory').text
timeout = root.find('timeout').text
region = root.find('region').text
credentials = root.find('credentials').text
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
    for functionDetail in function:
        if functionDetail.tag == 'trigger':
            functionDict['triggerType'] = functionDetail.get('type')
            for triggerDetail in functionDetail:
                functionDict[triggerDetail.tag] = triggerDetail.text
            continue
        functionDict[functionDetail.tag] = functionDetail.text
    functionDict['environment'] = set()
    functionDict['path'] = []
    functions.append(functionDict)

newFunctions = functions[:]
bucketsNeeded = []

def getTriggeredByFunction(functionID, functions):
    for pos, function in enumerate(functions):
        if function['id'] == functionID:
            return function, pos

for pos, function in enumerate(functions):
    function['environment'].add('PROJECT_ID')
    if function['triggerType'] == 'http':
        triggeredByFunctionID = function['triggeredBy']
        triggeredByFunction, newPosition = getTriggeredByFunction(triggeredByFunctionID, newFunctions)
        triggeredByFunction['environment'].add('HTTP_PATH')
        triggeredByFunction['path'].append(function['handler'])
    elif function['triggerType'] == 'gcstorage':
        if function['bucketName'] not in bucketsNeeded:
            bucketsNeeded.append(function['bucketName'])

# writing the serverless.yml file
filecontent = ""
providerDetails = providerDetails.replace("<serviceName>", serviceName)
providerDetails = providerDetails.replace("<providerName>", provider)
providerDetails = providerDetails.replace("<runtime>", runtime)
providerDetails = providerDetails.replace("<memorySize>", memory)
providerDetails = providerDetails.replace("<timeout>", timeout)
providerDetails = providerDetails.replace("<region>", region)
providerDetails = providerDetails.replace("<project>", project)
providerDetails = providerDetails.replace("<credentials>", credentials)

filecontent += providerDetails
filecontent += pluginsEtc
if bucketsNeeded:
    filecontent += resourcesHeader

for bucket in bucketsNeeded:
    toWrite = bucketTemplate.replace("<bucketName>",bucket)
    filecontent += toWrite

filecontent += functionsHeader
for function in newFunctions:
    toWrite = functionBasicTemplate.replace("<handlerName>",function['handler'])
    filecontent += toWrite
    filecontent += eventsHeader
    if function['triggerType'] == 'http' or function['triggerType'] == None:
        toWrite = httpEventTemplate
        filecontent += toWrite
    elif function['triggerType'] == 'gcstorage':
        toWrite = gcstorageEventTemplate.replace("<bucketName>",function['bucketName'])
        filecontent += toWrite
    elif function['triggerType'] == 'gcpubsub':
        toWrite = gcpubsubEventTemplate.replace("<topicName>",function['topicName'])
        filecontent += toWrite
    if "environment" in function:
        filecontent += environmentHeader
        for var in function["environment"]:
            if var == "HTTP_PATH":
                for path in function['path']:
                    toWrite = HTTP_PATH.replace("<path>",path)
                    filecontent += toWrite
            elif var == "PROJECT_ID":
                toWrite = PROJECT_ID
                filecontent += toWrite

os.chdir(input_dir)
f = open("serverless.yml","w+")
f.write(filecontent)
f.close()

output = os.popen('npm ls --depth=0 -s').read()
if 'serverless-google-cloudfunctions' not in output:
    print("Installing dependencies...")
    os.system("npm install --save serverless-google-cloudfunctions")

print("Your application is being deployed...")
output = os.popen('serverless deploy').read()
obj = re.search('https://([a-zA-Z0-9-.]*)(/func1)',output)
method = 'GET'
try:
    url = obj.group(1)
except:
    print("Serverless deploy ERROR")
    print(output)
    exit()
path = obj.group(2)
print(url)
print(path)
print("\nJMeter output:")
print("-"*100)
run_workload(url, method, path, loopCount, noOfUsers, rampUpTime)

start = Timestamp()
start.GetCurrentTime()
start_in_time = time.time()
os.system(jmeter_bin+"/jmeter -n -t "+jmeter_script+" -l output.csv -e -o output")

client = trace_service_client.TraceServiceClient.from_service_account_json(credentials)
print("\nPolling to get trace data...")
time.sleep(60)
# print(list(client.list_traces(project)))
no_of_traces = 0
traces = {}
for element in client.list_traces(project, start_time=start):
    # process element
    no_of_traces += 1
    trace = client.get_trace(project, element.trace_id)
    name = trace.spans[0].name
    seconds = trace.spans[0].end_time.seconds - trace.spans[0].start_time.seconds 
    nanos = trace.spans[0].end_time.nanos - trace.spans[0].start_time.nanos
    duration = seconds*1000 + nanos/1000000
    # print(duration, "ms")
    if name in traces.keys():
        traces[name]["count"]+=1
        traces[name]["responseTime"]+=duration
    else:
        traces[name] = {}
        traces[name]["count"]=1
        traces[name]["responseTime"]=duration
    # print("-"*100)
print("no of traces:", no_of_traces)

for name in traces.keys():
    avg = traces[name]["responseTime"]/traces[name]["count"]
    if name[0] != "/":
        print("-"*100)
        print(name, ":", avg, "ms")

def list_time_series(project_id, metric_type, start_time, div, unit):
    client = monitoring_v3.MetricServiceClient.from_service_account_json(credentials)
    project_name = client.project_path(project_id)
    interval = monitoring_v3.types.TimeInterval()
    now = time.time()
    interval.end_time.seconds = int(now)
    interval.end_time.nanos = int(
        (now - interval.end_time.seconds) * 10**9)
    interval.start_time.seconds = int(start_time)
    interval.start_time.nanos = int(
        (start_time - interval.start_time.seconds) * 10**9)
    metric = 'metric.type = "'+metric_type+'"'
    results = client.list_time_series(
        project_name,
        metric,
        interval,
        monitoring_v3.enums.ListTimeSeriesRequest.TimeSeriesView.FULL)
    for result in results:
        print("-"*100)
        print(result.resource.labels['function_name'])
        count = 0
        sum = 0.0
        for item in result.points:
            # print(item.value.distribution_value.count)
            # print(item.value.distribution_value.mean)
            count += item.value.distribution_value.count
            sum += (item.value.distribution_value.count*item.value.distribution_value.mean)
        print("avg: ", (sum/count)/div, unit)

#print("Waiting awhile before polling...")
time.sleep(200)
print("\nFunction memory usage (MB)\n")
list_time_series(project, "cloudfunctions.googleapis.com/function/user_memory_bytes", start_in_time, 1024**2, "MB")
print("\nFunction execution time (ms)\n")
list_time_series(project, "cloudfunctions.googleapis.com/function/execution_times", start_in_time, 10**6, "ms")

if toNotRemove == False:
    os.system('serverless remove')
    os.system('rm -rf output/')
    os.system('rm -f output.csv serverless.yml jmeter.log')