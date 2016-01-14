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

from octane.util import docker
from octane.util import subprocess


def add_releases(client, **context):
    data, _ = docker.run_in_container(
        "nailgun",
        ["cat", "/usr/share/fuel-openstack-metadata/openstack.yaml"],
        stdout=subprocess.PIPE)
    fixtures = yaml.load(data)
    base_release_fields = fixtures[0]['fields']
    for fixture in fixtures[1:]:
        data = base_release_fields.copy()
        data.update(fixture['fields'])
        client.create_release(data)
