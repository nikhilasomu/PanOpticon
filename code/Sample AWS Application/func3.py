import invoke_methods

def func3(event, context):
    print(event)
    invoke_methods.insert_into_dynamo_db("table123")