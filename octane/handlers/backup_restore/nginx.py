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


_PARAMS = [
    ("/var/lib/fuel/keys/master/nginx/nginx.crt", "nginx.crt"),
    ("/var/lib/fuel/keys/master/nginx/nginx.key", "nginx.key"),
]


def backup(archive):
    for path, tag in _PARAMS:
        archivate.archivate_container_cmd_output(
            archive, "nginx", "cat {0}".format(path), "nginx/{0}".format(tag))
