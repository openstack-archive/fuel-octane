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

from fuelclient import client
from fuelclient import fuelclient_settings

from octane.util import fuel_client


def test_simple_overwrite(mocker):

    class TestContext(object):

        user = "test user"
        password = "test password"

    conf = fuelclient_settings.get_settings()

    client_val = "Not empty val"

    assert conf.KEYSTONE_USER == client.APIClient.user
    assert conf.KEYSTONE_PASS == client.APIClient.password
    assert client.APIClient._session is None
    assert client.APIClient._keystone_client is None

    client.APIClient._session = client.APIClient._keystone_client = client_val

    with fuel_client.set_auth_context(TestContext()):
        assert TestContext.user == client.APIClient.user
        assert TestContext.password == client.APIClient.password
        assert client.APIClient._session is None
        assert client.APIClient._keystone_client is None

        client.APIClient._session = client_val
        client.APIClient._keystone_client = client_val

    assert conf.KEYSTONE_USER == client.APIClient.user
    assert conf.KEYSTONE_PASS == client.APIClient.password
    assert client.APIClient._session is None
    assert client.APIClient._keystone_client is None
