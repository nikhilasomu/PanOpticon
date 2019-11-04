import invoke_methods

def func4(event, context):
    print(event)
    invoke_methods.publish_message_sns("topic123", "hello from appln123")