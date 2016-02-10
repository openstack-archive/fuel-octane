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
import sys

from octane.commands import backup
from octane.handlers import backup_restore


@pytest.mark.parametrize("cmd,archivators,password", [
    ("fuel-backup", backup_restore.ARCHIVATORS, "password"),
    ("fuel-repo-backup", backup_restore.REPO_ARCHIVATORS, None),
])
@pytest.mark.parametrize("path", [None, "backup_file"])
def test_parser_empty(mocker, octane_app, cmd, archivators, path, password):
    m1 = mocker.patch('octane.commands.backup.backup')
    m1.return_value = 2
    params = [cmd]
    if path:
        params += ["--to", path]
    if password:
        params += ["--password", password]
    octane_app.run(params)
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m1.assert_called_once_with(path, archivators, password)


@pytest.mark.parametrize("path,mode", [
    ("path", "w|"),
    ("path.gz", "w|gz"),
    ("path.bz2", "w|bz2"),
    ("path.hz2", "w|"),
    (None, "w|"),
])
@pytest.mark.parametrize("password", [None, "password"])
def test_backup_admin_node_backup_file(
        mocker, mock_open, path, mode, password):
    manager = mocker.Mock()
    tar_obj = mocker.patch("tarfile.open")
    tmp_file = mocker.patch("tempfile.TemporaryFile")
    encryption_mock = mocker.patch("octane.util.encryption.encrypt_io")
    backup.backup(path, [manager], password)
    manager.assert_called_once_with(tar_obj.return_value)
    manager.return_value.backup.assert_called_once_with()
    if password:
        fileobj = tmp_file.return_value
        tar_obj.assert_called_once_with(fileobj=fileobj, mode=mode)
        if path:
            encryption_mock.assert_called_once_with(
                fileobj, mock_open.return_value, password)
        else:
            encryption_mock.assert_called_once_with(
                fileobj, sys.stdout, password)
    else:
        if path:
            fileobj = mock_open.return_value
        else:
            fileobj = sys.stdout
        tar_obj.assert_called_once_with(fileobj=fileobj, mode=mode)
        assert not encryption_mock.called
    if path:
        mock_open.assert_called_once_with(path, "w")
    else:
        assert not mock_open.called
