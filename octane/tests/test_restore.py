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

from octane.commands import restore


@pytest.mark.parametrize("params,call_params", [
    ([], None),
    (["--from", "path"], None),
    (["--from", "path", "-p", "password"], ("path", "password")),
    (["--from", "path", "--password", "password"], ("path", "password")),
])
def test_parser(mocker, octane_app, params, call_params):
    restore_mock = mocker.patch('octane.commands.restore.restore_admin_node')
    try:
        octane_app.run(["restore"] + params)
    except Exception:
        assert not restore_mock.called
        assert call_params is None
    else:
        restore_mock.assert_called_once_with(*call_params)


def test_restore_admin_node(mocker):
    context_mock = mocker.patch("octane.handlers.backup_restore.Context")
    tar_mock = mocker.patch("tarfile.open")
    archivator_mock_1 = mocker.Mock()
    archivator_mock_2 = mocker.Mock()
    mocker.patch(
        "octane.handlers.backup_restore.ARCHIVATORS",
        new=[archivator_mock_1, archivator_mock_2]
    )
    pwd = "password"
    path = "path"
    restore.restore_admin_node(path, pwd)
    tar_mock.assert_called_once_with(path)
    context_mock.assert_called_once_with(password=pwd)
    archivator_mock_1.assert_called_once_with(tar_mock.return_value)
    archivator_mock_2.assert_called_once_with(tar_mock.return_value)
    archivator_mock_1.post_restore_action(context_mock.return_value)
    archivator_mock_2.post_restore_action(context_mock.return_value)
