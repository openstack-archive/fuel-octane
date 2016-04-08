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

import yaml


def merge_dicts(base_dict, update_dict):
    result = base_dict.copy()
    for key, val in update_dict.iteritems():
        if key not in result or not isinstance(result[key], dict):
            result[key] = val
        else:
            result[key] = merge_dicts(result[key], val)
    return result


def get_astute_dict():
    with open("/etc/fuel/astute.yaml", "r") as current:
        return yaml.load(current)
