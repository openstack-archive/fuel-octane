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

from octane.commands import enable_release


@pytest.mark.parametrize("release_id,password",
                         [(1, 'test_pass'),
                          (1, None),
                          (None, None)])
def test_parser(mocker, octane_app, release_id, password):
    command = "enable-release"
    context = backup_restore.NailgunCredentialsContext(
        password=password, user="admin")
    enable_release_mock = mocker.patch("octane.commands.enable_release")
    params = [command, "--id", release_id, "--admin-password", password]
    try:
        octane_app.run(params)
    else:
        enable_release_mock.assert_called_once_with(release_id, context)
