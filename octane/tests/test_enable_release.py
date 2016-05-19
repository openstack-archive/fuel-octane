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

from octane.commands.enable_release import enable_release
from octane import magic_consts


@pytest.mark.parametrize("release_id,password",
                         [('1', 'test_pass'),
                          ('1', ''),
                          ('', '')])
def test_parser(mocker, octane_app, release_id, password):
    command = "enable-release"
    get_context_mock = mocker.patch(
        "octane.commands.enable_release.EnableReleaseCommand.get_context")
    context_mock = mocker.patch(
        "octane.handlers.backup_restore.NailgunCredentialsContext")
    get_context_mock.return_value = context_mock
    enable_release_mock = mocker.patch(
        "octane.commands.enable_release.enable_release")
    params = [command, "--id", release_id, "--admin-password", password]
    if release_id and password:
        try:
            octane_app.run(params)
        except Exception:
            raise
        else:
            enable_release_mock.assert_called_once_with(release_id,
                                                        context_mock)
    else:
        with pytest.raises(AssertionError):
            octane_app.run(params)


@pytest.mark.parametrize("release_id,data", [
    (1, {'state': 'manageonly', }),
    (1, {'state': 'available', }),
    (1, {'state': 'unavailable', }),
    (1, {'nostate': '', }),
])
def test_enable_release(mocker, release_id, data):
    release_url = "/reseases/{0}".format(release_id)
    context_class_mock = mocker.patch(
        "octane.handlers.backup_restore.NailgunCredentialsContext")
    context_mock = context_class_mock()
    set_auth_context_mock = mocker.patch(
        "octane.util.fuel_client.set_auth_context")
    get_request_mock = mocker.patch(
        "fuelclient.client.APIClient.get_request")
    put_request_mock = mocker.patch(
        "fuelclient.client.APIClient.put_request")
    get_request_mock.return_value = data

    enable_release(release_id, context_mock)
    set_auth_context_mock.assert_called_once_with(context_mock)
    if data.get("state") == magic_consts.RELEASE_STATUS_MANAGED:
        data['state'] = magic_consts.RELEASE_STATUS_ENABLED
        put_request_mock.assert_called_once_with(release_url, data)
