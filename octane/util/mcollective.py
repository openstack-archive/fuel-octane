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

import json

from octane.util import subprocess


def get_mco_ping_status():
    cmd = ["mco", "rpc", "rpcutil", "ping", "--json"]
    with subprocess.popen(cmd, stdout=subprocess.PIPE) as proc:
        return json.load(proc.stdout)


def compair_mco_ping_statuses(orig_status, new_status):
    orig_ids = {resp["sender"] for resp in orig_status}
    new_ids = {resp["sender"] for resp in new_status}
    offline = orig_ids - new_ids
    return offline
