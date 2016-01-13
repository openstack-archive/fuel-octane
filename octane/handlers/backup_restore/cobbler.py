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

from octane.util import archivate
from octane.util import subprocess


def backup(archive):
    stdout = subprocess.call_output(
        [
            "dockerctl",
            "shell",
            "cobbler",
            "ls",
            "/var/lib/cobbler/config/systems.d/",
        ])
    nodes = stdout.split()
    for node in nodes:
        archivate.archivate_container_cmd_output(
            archive,
            "cobbler",
            "cat /var/lib/cobbler/config/systems.d/{0}".format(node),
            "cobbler/systems.d/{0}".format(node))
