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
from octane.handlers.backup_restore import astute
from octane import magic_consts


@pytest.mark.parametrize("path,is_file", [
    (None, False),
    ("path", False),
    ("path", True),
])
@pytest.mark.parametrize("command, archivators, password_required", [
    ("fuel-restore", backup_restore.ARCHIVATORS, True),
    ("fuel-repo-restore", backup_restore.REPO_ARCHIVATORS, False),
])
@pytest.mark.parametrize("password", [None, "password"])
def test_parser(
        mocker, octane_app, path, is_file, command, archivators,
        password, password_required):
    if password and password_required:
        context = backup_restore.NailgunCredentialsContext(
            user="admin", password=password)
        mocker.patch(
            "octane.handlers.backup_restore.NailgunCredentialsContext",
            return_value=context)
    else:
        context = backup_restore.BaseContext()
        mocker.patch(
            "octane.handlers.backup_restore.BaseContext",
            return_value=context)
    restore_mock = mocker.patch('octane.commands.restore.restore_data')
    mocker.patch("os.path.isfile", return_value=is_file)
    params = [command]
    if path:
        params += ["--from", path]
    if password and password_required:
        params += ["--admin-password", password]
    try:
        octane_app.run(params)
    except AssertionError:  # parse error, app returns 2
        assert not restore_mock.called
        assert not password or path is None
    except ValueError:  # Invalid path to backup file
        assert not restore_mock.called
        assert not is_file
    else:
        restore_mock.assert_called_once_with(path, archivators, context)
        assert path is not None
        assert is_file


def test_restore_data(mocker):
    tar_mock = mocker.patch("tarfile.open")
    archivator_mock_1 = mocker.Mock()
    archivator_mock_2 = mocker.Mock()
    path = "path"
    restore.restore_data(path, [archivator_mock_1, archivator_mock_2], None)
    tar_mock.assert_called_once_with(path)
    for arch_mock in [archivator_mock_1, archivator_mock_2]:
        arch_mock.assert_has_calls([
            mock.call(tar_mock.return_value, None),
            mock.call().pre_restore_check(),
            mock.call().restore()])


@pytest.mark.parametrize("backup_ip,current_ip", [
    ("10.21.10.2", "10.21.10.2"),
    ("10.21.10.2", "10.21.10.12"),
])
def test_astute_checker(
        mocker, mock_open, backup_ip, current_ip):
    mocker.patch(
        "octane.util.docker.get_docker_container_names",
        return_value=magic_consts.RUNNING_REQUIRED_CONTAINERS)
    tar_mock = mocker.Mock()
    mocker.patch.object(
        astute.AstuteArchivator,
        "get_backup_dict",
        return_value={"ADMIN_NETWORK": {"ipaddress": backup_ip}}
    )
    mocker.patch.object(
        astute.AstuteArchivator,
        "get_current_dict",
        return_value={"ADMIN_NETWORK": {"ipaddress": current_ip}}
    )
    archivator = astute.AstuteArchivator(tar_mock)
    if backup_ip == current_ip:
        archivator.pre_restore_check()
    else:
        with pytest.raises(Exception) as exc:
            archivator.pre_restore_check()
        assert 'Restore allowed on machine with same ipaddress. ' \
            'Use fuel-menu to set up ipaddress to {0}'.format(
                backup_ip) == exc.value.message
