providerDetails = '''service: <serviceName>

provider:
  name: <providerName>
  runtime: <runtime>
  memorySize: <memorySize>
  timeout: <timeout>
  region: <region>
  tracing: 
    lambda: Active\n'''

customVariables = '''custom:
  stage: ${opt:stage, self:provider.stage}
  region: ${opt:region, self:provider.region}\n'''

iamRoleStatementsHeader = '''  iamRoleStatements:\n'''

xrayPermissions = '''    - Effect: Allow
      Action:
        - xray:PutTraceSegments
        - xray:PutTelemetryRecords
      Resource:
        - "*"\n'''

s3Permissions = '''    - Effect: Allow
      Action:
        - s3:PutObject
      Resource: arn:aws:s3:::*\n'''

dynamodbPermissions = '''    - Effect: Allow
      Action:
        - dynamodb:PutItem
        - dynamodb:DescribeTable
      Resource: arn:aws:dynamodb:*:*:table/*\n'''

snsPermissions = '''    - Effect: Allow
      Action:
        - sns:Publish
        - sns:Subscribe
      Resource: arn:aws:sns:*:*:*\n'''

sqsPermissions = '''    - Effect: Allow
      Action:
        - sqs:SendMessage
      Resource: arn:aws:sqs:*:*:*\n'''

sdkPermissions = '''    - Effect: Allow
      Action:
        - lambda:InvokeFunction
        - lambda:InvokeAsync
      Resource: "*"\n'''

resourcesHeader = '''resources:
  Resources:\n'''

sqsResource = '''    <queueName>:
      Type: "AWS::SQS::Queue"
      Properties:
        QueueName: <queueName>\n'''

dynamodbResourceFirstHalf = '''    <tableName>:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: <tableName>
        AttributeDefinitions:\n'''

dynamodbAttributeTemplate = '''          - AttributeName: <attributeName>
            AttributeType: <attributeType>\n'''

dynamodbKeyAttribute = '''        KeySchema:
          - AttributeName: <attributeName>
            KeyType: HASH\n'''

dynamodbResourceSecondHalf = '''        ProvisionedThroughput:
          ReadCapacityUnits: 1
          WriteCapacityUnits: 1
        StreamSpecification:
          StreamViewType: NEW_AND_OLD_IMAGES\n'''

functionsHeader = '''functions:\n'''

functionBasicTemplate = '''  <functionName>:
    handler: <functionName>.<handlerName>\n'''

eventsHeader = '''    events:\n'''

httpEventTemplate = '''      - http:
          path: <path>
          method: <method>
          integration: lambda\n'''

s3EventTemplate = '''      - s3: <bucketName>\n'''

dynamodbEventTemplate = '''      - stream:
          type: dynamodb
          arn:
            Fn::GetAtt: [<tableName>, StreamArn]\n'''

snsEventTemplate = '''      - sns: <topicName>\n'''

sqsEventTemplate = '''      - sqs:
          arn:
            Fn::GetAtt:
              - <queueName>
              - Arn\n'''

environmentVarHeader = '''    environment:\n'''

HTTP_PATH = '''      <path>: 
        Fn::Join:
        - ""
        - - "https://"
          - Ref: "ApiGatewayRestApi"
          - ".execute-api.${self:custom.region}.amazonaws.com/${self:custom.stage}/<path>"\n'''

SNS_TOPIC = '''      <topicName1>: 
        Ref: SNSTopic<topicName2>\n''' #first letter capitalized in topic name

SQS_QUEUE = '''      <queueName>: 
        Ref: <queueName>\n'''

LAMBDA = '''      <functionName>: "${self:service}-${self:custom.stage}-<functionName>"\n'''
