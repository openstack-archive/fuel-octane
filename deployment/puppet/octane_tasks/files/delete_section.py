#!/usr/bin/python

import yaml
import sys

target_file = sys.argv[1]
section = sys.argv[2]
subsection = sys.argv[3]

try:
    with open(target_file,'r+') as f:
        data = yaml.load(f)
        del data[section][subsection]

    with open(target_file,'w+') as f:
        yaml.dump(data,f,default_flow_style=False)
except KeyError as e:
    print "Failed to find key: {0}".format(e)
