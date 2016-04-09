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

import pytest

import fuelclient
from fuelclient import client
from fuelclient import fuelclient_settings

from octane.util import fuel_client


class TestContext(object):

    user = "test user"
    password = "test password"


def skipif_not_equal(version):
    reason = "requires fuelclient=={0}".format(version)
    return pytest.mark.skipif(fuelclient.__version__ != version, reason=reason)


@pytest.mark.parametrize(("auth_context", "is_legacy"), [
    skipif_not_equal("8.0.0")((fuel_client.set_auth_context_80, True)),
    skipif_not_equal("9.0.0")((fuel_client.set_auth_context_90, False)),
])
def test_simple_overwrite(auth_context, is_legacy):
    conf = fuelclient_settings.get_settings()

    client_val = "Not empty val"

    if is_legacy:
        assert conf.KEYSTONE_USER == client.APIClient.user
        assert conf.KEYSTONE_PASS == client.APIClient.password
    assert client.APIClient._session is None
    assert client.APIClient._keystone_client is None

    client.APIClient._session = client.APIClient._keystone_client = client_val

    with auth_context(TestContext()):
        if is_legacy:
            assert TestContext.user == client.APIClient.user
            assert TestContext.password == client.APIClient.password
        else:
            assert TestContext.user == conf.OS_USERNAME
            assert TestContext.password == conf.OS_PASSWORD
        assert client.APIClient._session is None
        assert client.APIClient._keystone_client is None

        client.APIClient._session = client_val
        client.APIClient._keystone_client = client_val

    if is_legacy:
        assert conf.KEYSTONE_USER == client.APIClient.user
        assert conf.KEYSTONE_PASS == client.APIClient.password
    assert client.APIClient._session is None
    assert client.APIClient._keystone_client is None
