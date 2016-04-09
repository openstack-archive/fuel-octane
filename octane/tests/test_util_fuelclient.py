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


class MockFuelClient80(mock.Mock):
    def initial_credentials(self, user, password):
        self.user = user
        self.password = password

    def assert_credentials(self, user, password):
        assert self.user == user
        assert self.password == password


class MockFuelClient90(mock.Mock):
    def initial_credentials(self, user, password):
        self._config['OS_USERNAME'] = user
        self._config['OS_PASSWORD'] = password

    def assert_credentials(self, user, password):
        assert self._config['OS_USERNAME'] == user
        assert self._config['OS_PASSWORD'] == password


class FakeSettings(object):
    def __init__(self):
        self.config = {}

    @property
    def OS_USERNAME(self):
        return self.config["OS_USERNAME"]

    @property
    def OS_PASSWORD(self):
        return self.config["OS_PASSWORD"]


@pytest.fixture
def mock_fuelclient_80(mocker):
    client = mocker.patch("fuelclient.client.APIClient",
                          new_callable=MockFuelClient80)
    client.mock_add_spec(
        ["user", "password", "_session", "_keystone_client"],
        spec_set=True,
    )
    return client


@pytest.fixture
def mock_fuelclient_90(mocker):
    get_settings = mocker.patch("fuelclient.fuelclient_settings.get_settings")
    get_settings.return_value = settings = FakeSettings()
    client = mocker.patch("fuelclient.client.APIClient",
                          new_callable=MockFuelClient90)
    client.mock_add_spec(
        ["user", "password", "_session", "_keystone_client", "_config"],
        spec_set=True,
    )
    client._config = settings.config
    return client


# NOTE(akscram): It's not possible to use fixtures in parametrized tests
# as parameters and I use them as common functions. For more information
# take a look on this: https://github.com/pytest-dev/pytest/issues/349
@pytest.mark.parametrize(("auth_context", "fuelclient_fixture"), [
    (fuel_client.set_auth_context_80, mock_fuelclient_80),
    (fuel_client.set_auth_context_90, mock_fuelclient_90),
])
def test_simple_overwrite(mocker, auth_context, fuelclient_fixture):
    def assert_client_state(user, password):
        mock_client.assert_credentials(user, password)

        assert mock_client._session is None
        assert mock_client._keystone_client is None

    mock_client = fuelclient_fixture(mocker)
    mock_client.initial_credentials("userA", "passwordA")
    context = mock.Mock(user="userB", password="passwordB",
                        spec=["user", "password"])

    with auth_context(context):
        assert_client_state(context.user, context.password)

        mock_client._session = mock.Mock()
        mock_client._keystone_client = mock.Mock()

    assert_client_state("userA", "passwordA")
