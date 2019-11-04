import os
import requests
import json
from google.cloud import storage
from google.cloud import pubsub_v1
from opencensus.trace import tracer as tracer_module		
from opencensus.trace.exporters import stackdriver_exporter		
from opencensus.trace.exporters.transports.background_thread import BackgroundThreadTransport		
		
projectID = os.environ['PROJECT_ID']		
exporter = stackdriver_exporter.StackdriverExporter(project_id=projectID, transport=BackgroundThreadTransport)


def trigger_http_endpoint(path, method, message={}):
    #include other methods if necessary
    httpEndpoint = os.environ[path]
    tracer = tracer_module.Tracer(exporter=exporter)
    with tracer.span(name=httpEndpoint) as tracerObj:
        headers = {
            'content-type': 'application/json',
            "content-length": str(len(message))
        }
        r = requests.post(httpEndpoint, data=json.dumps(message), headers=headers)
    print(r.status_code)

def upload_to_gcf_bucket(bucketName, filename="log.txt"):
    tracer = tracer_module.Tracer(exporter=exporter)
    with tracer.span(name=bucketName) as tracerObj:
        client = storage.Client()
        bucket = client.get_bucket(bucketName)
        blob = bucket.blob(filename)
        blob.upload_from_filename(filename)

def publish_msg_to_gcf_pubsub(topicName, message="Default message"):
    projectID = os.environ['PROJECT_ID']
    tracer = tracer_module.Tracer(exporter=exporter)
    with tracer.span(name=topicName) as tracerObj:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(projectID, topicName)
        publisher.publish(topic_path, data=message.encode('utf-8'))