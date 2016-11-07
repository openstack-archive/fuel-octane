#!/usr/bin/python

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

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
