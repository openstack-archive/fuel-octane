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

from octane.util import helpers
from octane.util import node as node_util
from octane.util import ssh


def remove_legacy_services(controller):
    output = node_util.run_with_openrc(
        ["cinder", "service-list", "--host", "rbd:volumes"], node=controller)
    services = helpers.parse_table_output(output)
    for service in services:
        if service["Host"] != "rbd:volumes" or service["State"] != "down":
            continue
        ssh.call(["cinder-manage", "service", "remove", service["Binary"],
                  service["Host"]], node=controller)
