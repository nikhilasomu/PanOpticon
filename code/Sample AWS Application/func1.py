import invoke_methods

def func1(event, context):
    print(event)
    invoke_methods.trigger_http_endpoint("path","post", {"appl":"123"})