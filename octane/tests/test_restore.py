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
@pytest.mark.parametrize("command, archivators, encrypted", [
    ("fuel-restore", backup_restore.ARCHIVATORS, True),
    ("fuel-repo-restore", backup_restore.REPO_ARCHIVATORS, False),
])
@pytest.mark.parametrize("password", ["password", None])
def test_parser(
        mocker, mock_open,
        octane_app, path,
        is_file, command,
        archivators, password,
        encrypted):
    restore_mock = mocker.patch('octane.commands.restore.restore')
    mocker.patch("os.path.isfile", return_value=is_file)
    params = [command]
    if path:
        params += ["--from", path]
    if password and encrypted:
        params += ["--password", password]
    try:
        octane_app.run(params)
    except AssertionError:  # parse error, app returns 2
        assert not restore_mock.called
        assert path is None or (password is None and encrypted)
    except ValueError:  # Invalid path to backup file
        assert not restore_mock.called
        assert not is_file
    else:
        if encrypted:
            restore_mock.assert_called_once_with(path, archivators, password)
        else:
            restore_mock.assert_called_once_with(path, archivators, None)
        assert path is not None
        assert is_file


@pytest.mark.parametrize("password", ["password", None])
def test_restore_data(mocker, mock_open, password):
    tar_mock = mocker.patch("tarfile.open")
    tmp_mock = mocker.patch("tempfile.TemporaryFile")
    enc_mock = mocker.patch("octane.util.encryption.decrypt_io")
    archivator_mock_1 = mocker.Mock()
    archivator_mock_2 = mocker.Mock()
    path = "path"
    restore.restore(path, [archivator_mock_1, archivator_mock_2], password)
    if password:
        tar_mock.assert_called_once_with(fileobj=tmp_mock.return_value)
        mock_open.assert_called_once_with(path)
        tmp_mock.assert_called_once_with()
        enc_mock.assert_called_once_with(
            mock_open.return_value, tmp_mock.return_value, password)
    else:
        tar_mock.assert_called_once_with(fileobj=mock_open.return_value)
        mock_open.assert_called_once_with(path)
        assert not tmp_mock.called
        assert not enc_mock.called
    for arch_mock in [archivator_mock_1, archivator_mock_2]:
        arch_mock.assert_has_calls([
            mock.call(tar_mock.return_value),
            mock.call().pre_restore_check(),
            mock.call().restore()])
