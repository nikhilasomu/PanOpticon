providerDetails = '''
service: <serviceName>

provider:
  name: <providerName>
  memorySize: <memorySize>
  timeout: <timeout>
  stage: dev
  runtime: <runtime>
  region: <region>
  project: <project>
  credentials: <credentials>'''

pluginsEtc = '''
plugins:
  - serverless-google-cloudfunctions
package:
  exclude:
    - node_modules/**
    - .gitignore
    - .git/**'''

resourcesHeader = '''
resources:
  resources:'''

bucketTemplate = '''
    - type: storage.v1.bucket
      name: <bucketName>'''

functionsHeader = '''
functions:'''

functionBasicTemplate = '''
  <handlerName>:
    handler: <handlerName>'''

eventsHeader = '''
    events:'''

httpEventTemplate = '''
      - http: path'''

gcpubsubEventTemplate = '''
      - event:
          eventType: providers/cloud.pubsub/eventTypes/topic.publish
          resource: "projects/${self:provider.project, ''}/topics/<topicName>"'''

gcstorageEventTemplate = '''
      - event:
          eventType: google.storage.object.finalize
          resource: "projects/${self:provider.project, ''}/buckets/<bucketName>"'''

environmentHeader = '''
    environment:'''

HTTP_PATH = '''
      <path>: "https://${self:provider.region}-${self:provider.project}.cloudfunctions.net/<path>"'''

PROJECT_ID = '''
      PROJECT_ID: "${self:provider.project}"'''