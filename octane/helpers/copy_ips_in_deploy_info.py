# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
import yaml


parser = argparse.ArgumentParser(description="ips copy script")
parser.add_argument('source_yaml', metavar='<file>', type=str,
                    help='source yaml file')
parser.add_argument('destination_yaml', metavar='<file>', type=str,
                    help='destination yaml file')
args = parser.parse_args()

with open(args.source_yaml, 'r') as source:
    source_yaml = yaml.load(source)

with open(args.destination_yaml, 'r') as dest:
    dest_yaml = yaml.load(dest)
    dest_yaml["management_vip"] = source_yaml["management_vip"]
    dest_yaml["public_vip"] = source_yaml["public_vip"]
    for i in source_yaml["nodes"]:
        for j in dest_yaml["nodes"]:
            if i["name"] == j["name"] and i["role"] in ["controller",
                                                        "primary-controller"]:
                j["internal_address"] = i["internal_address"]
                j["public_address"] = i["public_address"]

with open(args.destination_yaml, 'w') as target:
    target.write(yaml.dump(dest_yaml, default_flow_style=False))
