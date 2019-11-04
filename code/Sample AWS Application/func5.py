import invoke_methods

def func5(event, context):
    print(event)
    invoke_methods.send_message_sqs("queue123", "hello from appln123")