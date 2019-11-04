import invoke_methods

def func2(event, context):
    print(event)
    invoke_methods.upload_file_to_bucket(1024, "nbucket123")
    return {
        "body": "appln123",
        "headers": {},
        "statusCode": 200
    }