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


def test_parser_empty(mocker, octane_app):
    m1 = mocker.patch('octane.commands.backup.backup_admin_node')
    m1.return_value = 2
    octane_app.run(["fuel-backup"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m1.assert_called_once_with(None)


def test_parser_not_empty(mocker, octane_app):
    m1 = mocker.patch('octane.commands.backup.backup_admin_node')
    m1.return_value = 2
    octane_app.run(["fuel-backup", "--to", "backup_file"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m1.assert_called_once_with("backup_file")


@pytest.mark.parametrize("path,mode", [
    ("path", "w|"),
    ("path.gz", "w|gz"),
    ("path.bz2", "w|bz2"),
    ("path.hz2", "w|"),
    (None, "w|"),
])
def test_backup_admin_node_backup_file(mocker, path, mode):
    manager = mocker.Mock()
    mocker.patch('octane.handlers.backup_restore.ARCHIVATORS', new=[manager])
    tar_obj = mocker.patch("tarfile.open")
    backup.backup_admin_node(path)
    manager.assert_called_once_with(tar_obj.return_value)
    manager.return_value.backup.assert_called_once_with()
    if path is not None:
        tar_obj.assert_called_once_with(path, mode)
    else:
        tar_obj.assert_called_once_with(fileobj=sys.stdout, mode=mode)
