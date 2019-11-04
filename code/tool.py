import sys, os
import xml.etree.ElementTree as et

def change_xml_attribute(root, property, value):
    for node in root.iter(property):
        node.text = value 
        return

if len(sys.argv) != 2:
    print("usage: python3 tool.py <input_dir>")
    exit(1)

input_dir = sys.argv[1]
input_file = sys.argv[1]+"/xml_input.xml"
parser = et.XMLParser(encoding="utf-8")
tree = et.parse(input_file, parser=parser)
root = tree.getroot()

provider = root.find('provider').text
memoryStart = int(root.find('memoryStart').text)
memoryStep = int(root.find('memoryStep').text)
memoryEnd = int(root.find('memoryEnd').text)


while memoryStart <= memoryEnd:
    #print("Starting execution for memory configuration:", memoryStart)
    root = et.parse(input_file)
    change_xml_attribute(root, 'memory', str(memoryStart))
    root.write(input_file, encoding='utf8', method='xml')
    if provider == "aws":
        os.system('python3 parse_aws_input_xml.py "'+input_dir+'"')
        memoryStart += memoryStep
    elif provider == "google":
        os.system('python3 parse_gcf_input_xml.py "'+input_dir+'"')
        memoryStart *= 2
