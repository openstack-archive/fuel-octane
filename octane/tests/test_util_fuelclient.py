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

import mock
import pytest

from octane.util import fuel_client


def mock_fuelclient_80(mocker, user, password):
    client = mocker.patch("fuelclient.client.APIClient",
                          new_callable=mock.Mock)
    client.mock_add_spec(
        ["user", "password", "_session", "_keystone_client"],
        spec_set=True,
    )
    client.user = user
    client.password = password
    return client, None


def mock_fuelclient_90(mocker, user, password):
    config = {
        'OS_USERNAME': user,
        'OS_PASSWORD': password,
    }
    get_settings = mocker.patch("fuelclient.fuelclient_settings.get_settings")
    get_settings.return_value.configure_mock(config=config, **config)
    get_settings.return_value.mock_add_spec(
        ["config", "OS_USERNAME", "OS_PASSWORD"],
        spec_set=True,
    )
    client = mocker.patch("fuelclient.client.APIClient",
                          new_callable=mock.Mock)
    client.mock_add_spec(["_session", "_keystone_client"], spec_set=True)
    return client, config


# NOTE(akscram): It's not possible to use fixtures in parametrized tests
# as parameters and I use them as common functions. For more information
# take a look on this: https://github.com/pytest-dev/pytest/issues/349
@pytest.mark.parametrize(("auth_context", "fuelclient_fixture", "legacy"), [
    (fuel_client.set_auth_context_80, mock_fuelclient_80, True),
    (fuel_client.set_auth_context_90, mock_fuelclient_90, False),
])
def test_simple_overwrite(mocker, auth_context, fuelclient_fixture, legacy):
    def assert_client_state(user, password):
        if legacy:
            assert mock_client.user == user
            assert mock_client.password == password
        else:
            assert mock_config['OS_USERNAME'] == user
            assert mock_config['OS_PASSWORD'] == password

        assert mock_client._session is None
        assert mock_client._keystone_client is None

    mock_client, mock_config = fuelclient_fixture(mocker, "userA", "passwordA")
    context = mock.Mock(user="userB", password="passwordB",
                        spec=["user", "password"])

    with auth_context(context):
        assert_client_state(context.user, context.password)

        mock_client._session = mock.Mock()
        mock_client._keystone_client = mock.Mock()

    assert_client_state("userA", "passwordA")
