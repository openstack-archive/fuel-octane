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
from octane.handlers import backup_restore


@pytest.mark.parametrize("path,is_file", [
    (None, False),
    ("path", False),
    ("path", True),
])
@pytest.mark.parametrize("command, archivators", [
    ("fuel-restore", backup_restore.ARCHIVATORS),
    ("fuel-repo-restore", backup_restore.REPO_ARCHIVATORS),
])
def test_parser(mocker, octane_app, path, is_file, command, archivators):
    restore_mock = mocker.patch('octane.commands.restore.restore_data')
    mocker.patch("os.path.isfile", return_value=is_file)
    params = [command]
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
        restore_mock.assert_called_once_with(path, archivators)
        assert path is not None
        assert is_file


def test_restore_data(mocker):
    tar_mock = mocker.patch("tarfile.open")
    archivator_mock_1 = mocker.Mock()
    archivator_mock_2 = mocker.Mock()
    path = "path"
    restore.restore_data(path, [archivator_mock_1, archivator_mock_2])
    tar_mock.assert_called_once_with(path)
    for arch_mock in [archivator_mock_1, archivator_mock_2]:
        arch_mock.assert_has_calls([
            mock.call().pre_restore_check(),
            mock.call().restore()])
