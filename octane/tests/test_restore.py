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

from octane.commands import restore


@pytest.mark.parametrize("path,is_file", [
    (None, False),
    ("path", False),
    ("path", True),
])
def test_parser(mocker, octane_app, path, is_file):
    restore_mock = mocker.patch('octane.commands.restore.restore_admin_node')
    mocker.patch("os.path.isfile", return_value=is_file)
    params = ["fuel-restore"]
    if path:
        params += ["--from", path]
    try:
        octane_app.run(params)
    except AssertionError:  # parse error, app returns 2
        assert not restore_mock.called
        assert path is None
    except ValueError:  # Invalid path to backup file
        assert not restore_mock.called
        assert not is_file
    else:
        restore_mock.assert_called_once_with(path)
        assert path is not None
        assert is_file


def test_restore_admin_node(mocker):
    tar_mock = mocker.patch("tarfile.open")
    archivator_mock_1 = mocker.Mock()
    archivator_mock_2 = mocker.Mock()
    mocker.patch(
        "octane.handlers.backup_restore.ARCHIVATORS",
        new=[archivator_mock_1, archivator_mock_2]
    )
    path = "path"
    restore.restore_admin_node(path)
    tar_mock.assert_called_once_with(path)
    for arch_mock in [archivator_mock_1, archivator_mock_2]:
        arch_mock.assert_has_calls([
            mock.call().pre_restore_check(),
            mock.call().restore(),
            mock.call().post_restore_action()])
