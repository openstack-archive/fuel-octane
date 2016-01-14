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

import collections
import json
import requests
import urlparse
import yaml

from keystoneclient.v2_0 import Client as keystoneclient

from octane.util import docker
from octane.util import subprocess


# Context class for executing actions, each action should
# work with instance of this class
Context = collections.namedtuple(
    "Context",
    # set up new context fields here
    [
        "password",
    ]
)


NAILGUN_URL = "http://127.0.0.1:8000"
KEYSTONE_URL = "http://127.0.0.1:5000/v2.0"
USERNAME = "admin"
TENANT_NAME = "admin"


def __post_data_to_nailgun(url, data, password):
    ksclient = keystoneclient(
        auth_url=KEYSTONE_URL,
        username="admin",
        password=password,
        tenant_name=TENANT_NAME
    )
    return requests.post(
        urlparse.urljoin(NAILGUN_URL, url),
        json.dumps(data),
        headers={
            "X-Auth-Token": ksclient.auth_token,
            "Content-Type": "application/json"
        })


def add_releases(context):
    data, _ = docker.run_in_container(
        "nailgun",
        ["cat", "/usr/share/fuel-openstack-metadata/openstack.yaml"],
        stdout=subprocess.PIPE)
    fixtures = yaml.load(data)
    base_release_fields = fixtures[0]['fields']
    for fixture in fixtures[1:]:
        release = base_release_fields.copy()
        release.update(fixture['fields'])
        __post_data_to_nailgun("/api/v1/releases/", release, context.password)
