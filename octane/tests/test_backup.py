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
import sys

from octane.commands import backup


def test_parser_empty(mocker, octane_app):
    m1 = mocker.patch('octane.commands.backup.backup_admin_node')
    m1.return_value = 2
    octane_app.run(["backup"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m1.assert_called_once_with(None)


def test_parser_not_empty(mocker, octane_app):
    m1 = mocker.patch('octane.commands.backup.backup_admin_node')
    m1.return_value = 2
    octane_app.run(["backup", "--to", "backup_file"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m1.assert_called_once_with("backup_file")


def _test_backup_admin_node(mocker, path):
    manager = mocker.Mock()
    backup_mock = mocker.patch('octane.commands.backup.backup_restore')
    backup_mock.MANAGERS = [manager]
    tar_obj = mocker.patch("tarfile.open")
    backup.backup_admin_node(path)
    manager.assert_called_once_with(tar_obj.return_value)
    manager.return_value.backup.assert_called_once_with()
    return tar_obj


def test_backup_admin_node_no_backup_file(mocker):
    tar_obj = _test_backup_admin_node(mocker, None)
    tar_obj.assert_called_once_with(fileobj=sys.stdout, mode="w|")


def test_backup_admin_node_backup_file(mocker):
    tar_obj = _test_backup_admin_node(mocker, "path")
    tar_obj.assert_called_once_with("path", "w|")


def test_backup_admin_node_gz_backup_file(mocker):
    tar_obj = _test_backup_admin_node(mocker, "path.gz")
    tar_obj.assert_called_once_with("path.gz", "w|gz")


def test_backup_admin_node_bz2_backup_file(mocker):
    tar_obj = _test_backup_admin_node(mocker, "path.bz2")
    tar_obj.assert_called_once_with("path.bz2", "w|bz2")
