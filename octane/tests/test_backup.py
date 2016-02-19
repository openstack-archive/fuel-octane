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
        octane_app.run(params)
        assert not octane_app.stdout.getvalue()
        assert not octane_app.stderr.getvalue()
        m1.assert_called_once_with(path, archivators)
    else:
        with pytest.raises(AssertionError):
            octane_app.run(params)


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
    tmp_file.return_value.__enter__.return_value = tmp_file
    move_mock = mocker.patch("shutil.move")
    dir_path = "/abs"
    abs_path = "{0}/{1}".format(dir_path, path)
    os_abs_path_mock = mocker.patch("os.path.abspath", return_value=abs_path)
    if empty:
        with pytest.raises(Exception) as exc:
            backup.backup(path, [manager])
        assert "Nothing to backup" == exc.value.message
    else:
        backup.backup(path, [manager])
    os_abs_path_mock.assert_called_once_with(path)
    manager.assert_called_once_with(tar_obj.return_value)
    manager.return_value.backup.assert_called_once_with()
    tmp_file.assert_called_once_with(dir=dir_path, prefix=".{0}.".format(path))
    if path is not None:
        tar_obj.assert_called_once_with(fileobj=tmp_file, mode=mode)
        if empty:
            assert not move_mock.called
        else:
            move_mock.assert_called_once_with(tmp_file.name, abs_path)
    else:
        tar_obj.assert_called_once_with(fileobj=sys.stdout, mode=mode)
        assert not move_mock.called
