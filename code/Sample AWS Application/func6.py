import invoke_methods

def func6(event, context):
    print(event)
    invoke_methods.invoke_lambda("func7", {"appln123":"nikhila"})