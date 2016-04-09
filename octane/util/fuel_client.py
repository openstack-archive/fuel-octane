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

import contextlib

import fuelclient
from fuelclient import client
from fuelclient import fuelclient_settings


@contextlib.contextmanager
def set_auth_context_80(auth_context):
    old_credentials = (client.APIClient.user, client.APIClient.password)
    client.APIClient.user = auth_context.user
    client.APIClient.password = auth_context.password
    client.APIClient._session = client.APIClient._keystone_client = None
    try:
        yield
    finally:
        (client.APIClient.user, client.APIClient.password) = old_credentials
        client.APIClient._session = client.APIClient._keystone_client = None


@contextlib.contextmanager
def set_auth_context_90(auth_context):
    settings = fuelclient_settings.get_settings()
    config = settings.config
    old_credentials = (settings.OS_USERNAME, settings.OS_PASSWORD)
    config['OS_USERNAME'] = auth_context.user
    config['OS_PASSWORD'] = auth_context.password
    client.APIClient._session = client.APIClient._keystone_client = None
    try:
        yield
    finally:
        (config['OS_USERNAME'], config['OS_PASSWORD']) = old_credentials
        client.APIClient._session = client.APIClient._keystone_client = None


# NOTE(akscram): The 9.0.0 release for fuelclient is not yet available
# on PyPI but to test it on master nodes with the 9.0 release some
# workaround is needed.
if fuelclient.__version__ == "8.0.0":
    set_auth_context = set_auth_context_80
else:
    set_auth_context = set_auth_context_90
