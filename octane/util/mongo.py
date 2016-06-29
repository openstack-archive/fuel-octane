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
import logging

from octane.util import env as env_util
from octane.util import ssh

LOG = logging.getLogger(__name__)


def check_cluster(node):
    # Find password in astute.yaml
    passwd = env_util.get_astute_yaml(None, node)['ceilometer']['db_password']

    # Fetch cluster info and load JSON object
    cluster_status_json = json.loads(
        ssh.call_output([
            "mongo", "-u", "admin",
            "-p", passwd, "admin", "--quiet", "--eval",
            "print(JSON.stringify(rs.status()))"], node=node))

    # Check status of every node
    for member in cluster_status_json["members"]:
        if not member["stateStr"] in ["PRIMARY", "SECONDARY"]:
            raise Exception("Status of {0} node is neither PRIMARY nor "
                            "SECONDARY. It looks like broken cluster. "
                            "Status is '{1}'.".format(
                                member["name"],
                                member["stateStr"]))
        else:
            LOG.debug("Status of {0} node is {1}".format(
                member["name"],
                member["stateStr"]))
