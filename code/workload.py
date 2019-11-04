import xml.etree.ElementTree as et

jmeter_script = ""
jmeter_bin = ""

def change_xml_attribute(root, property, attribute, attribute_value, value):
    for node in root.iter(property):
        if node.attrib[attribute] == attribute_value:
            node.text = value 
            return

def run_workload(url, method, path, loopCount, noOfUsers, rampUpTime):
    root = et.parse(jmeter_script)
    change_xml_attribute(root, 'stringProp', 'name', 'HTTPSampler.domain', url)
    change_xml_attribute(root, 'stringProp', 'name', 'HTTPSampler.path', path)
    change_xml_attribute(root, 'stringProp', 'name', 'HTTPSampler.method', method)
    change_xml_attribute(root, 'stringProp', 'name', 'LoopController.loops', loopCount)
    change_xml_attribute(root, 'stringProp', 'name', 'ThreadGroup.num_threads', noOfUsers)
    change_xml_attribute(root, 'stringProp', 'name', 'ThreadGroup.ramp_time', rampUpTime)
    root.write(jmeter_script, encoding='utf8', method='xml')