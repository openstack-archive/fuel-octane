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


@pytest.mark.parametrize("cmd,archivators", [
    ("fuel-backup", backup_restore.ARCHIVATORS),
    ("fuel-repo-backup", backup_restore.REPO_ARCHIVATORS),
])
@pytest.mark.parametrize("path", [None, "backup_file"])
def test_parser_empty(mocker, octane_app, cmd, archivators, path):
    m1 = mocker.patch('octane.commands.backup.backup')
    m1.return_value = 2
    params = [cmd]
    if path:
        params += ["--to", path]
    try:
        octane_app.run(params)
    except AssertionError:
        assert path is None
    else:
        assert not octane_app.stdout.getvalue()
        assert not octane_app.stderr.getvalue()
        m1.assert_called_once_with(path, archivators)


@pytest.mark.parametrize("path,mode", [
    ("path", "w|"),
    ("path.gz", "w|gz"),
    ("path.bz2", "w|bz2"),
    ("path.hz2", "w|"),
])
@pytest.mark.parametrize("empty", [True, False])
def test_backup_admin_node_backup_file(mocker, path, mode, empty):
    manager = mocker.Mock()
    tar_obj = mocker.patch("tarfile.open")
    if empty:
        tar_obj.return_value.getmembers.return_value = []
    tmp_file = mocker.patch("tempfile.NamedTemporaryFile")
    unlink_mock = mocker.patch("os.unlink")
    mocker.patch("os.path.isfile", return_value=True)
    move_mock = mocker.patch("shutil.move")
    try:
        backup.backup(path, [manager])
    except AssertionError as exc:
        assert "backup is empty" == exc.msg and empty
    manager.assert_called_once_with(tar_obj.return_value)
    manager.return_value.backup.assert_called_once_with()
    if path is not None:
        tmp_file.assert_called_once_with(delete=False)
        tar_obj.assert_called_once_with(
            fileobj=tmp_file.return_value, mode=mode)
        unlink_mock.assert_called_once_with(tmp_file.return_value.name)
        if empty:
            assert not move_mock.called
        else:
            move_mock.assert_called_once_with(tmp_file.return_value.name, path)
    else:
        tar_obj.assert_called_once_with(fileobj=sys.stdout, mode=mode)
        assert not tmp_file.called
        assert not unlink_mock.called
        assert not move_mock.called
