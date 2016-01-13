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

import os
import pytest

from octane.handlers.backup_restore import astute
from octane.handlers.backup_restore import cobbler
from octane.handlers.backup_restore import fuel_keys
from octane.handlers.backup_restore import fuel_uuid
from octane.handlers.backup_restore import nginx
from octane.handlers.backup_restore import postgres
from octane.handlers.backup_restore import puppet
from octane.handlers.backup_restore import ssh
from octane.handlers.backup_restore import version
from octane.util import subprocess


@pytest.mark.parametrize("cls,path,name", [
    (astute.AstuteArchivator, "/etc/fuel/astute.yaml", "astute/astute.yaml"),
    (fuel_keys.FuelKeysArchivator, "/var/lib/fuel/keys", "fuel_keys"),
    (
        fuel_uuid.FuelUUIDArchivator,
        "/etc/fuel/fuel-uuid",
        "fuel_uuid/fuel-uuid"
    ),
    (ssh.SshArchivator, "/root/.ssh/", "ssh"),
])
def test_path_backup(mocker, cls, path, name):
    test_archive = mocker.Mock()
    cls(test_archive).backup()
    test_archive.add.assert_called_once_with(path, name)


@pytest.mark.parametrize(
    "cls,banned_files,backup_directory,allowed_files, container", [
        (
            cobbler.CobblerArchivator,
            ["default.json"],
            "/var/lib/cobbler/config/systems.d/",
            None,
            "cobbler"
        ),
        (
            nginx.NginxArchivator,
            None,
            "/var/lib/fuel/keys/",
            None,
            "nginx"
        ),
    ])
def test_container_backup(
        mocker, cls, banned_files, backup_directory, allowed_files, container):
    test_archive = mocker.Mock()
    docker_mock = mocker.patch("octane.handlers.backup_restore.base.docker")
    archive_mock = mocker.patch(
        "octane.handlers.backup_restore.base.archivate")
    data_lst = (banned_files or []) + (allowed_files or []) + ["tmp1", "tmp2"]
    stdout_data_lst = [os.path.join(backup_directory, f) for f in data_lst]
    data = " ".join(stdout_data_lst)
    process = docker_mock.in_container.return_value.__enter__.return_value
    process.communicate.return_value = data, None

    if allowed_files:
        files_to_archive = [d for d in data_lst if d in allowed_files]
    elif banned_files:
        files_to_archive = [d for d in data_lst if d not in banned_files]
    else:
        files_to_archive = data_lst
    backuped_files = set()

    def foo(archive, container_name, cmd, backup_dir):
        assert archive is test_archive
        assert container == container_name
        _, path = cmd
        assert _ == "cat"
        assert path[:len(backup_directory)] == backup_directory
        assert backup_dir[:len(container)] == container
        filename = path[len(backup_directory):].strip("\/")
        backuped_files.add(path[len(backup_directory):])
        assert filename == backup_dir[len(container):].strip("\/")
    archive_mock.archivate_container_cmd_output.side_effect = foo
    cls(test_archive).backup()
    docker_mock.in_container.assert_called_once_with(
        container,
        ["find", backup_directory, "-type", "f"],
        stdout=subprocess.PIPE
    )
    for filename in files_to_archive:
        assert filename in backuped_files


@pytest.mark.parametrize("cls,db", [
    (postgres.NailgunArchivator, "nailgun"),
    (postgres.KeystoneArchivator, "keystone"),
])
def test_posgres_archivator(mocker, cls, db):
    test_archive = mocker.Mock()
    archive_mock = mocker.patch(
        "octane.handlers.backup_restore.base.archivate")
    cls(test_archive).backup()
    archive_mock.archivate_container_cmd_output.assert_called_once_with(
        test_archive,
        "postgres",
        ["sudo", "-u", "postgres", "pg_dump", "-C", db],
        "postgres/{0}.sql".format(db))


@pytest.mark.parametrize("cls, path, tag", [
    (puppet.PuppetArchivator, "/etc/puppet", "puppet"),
    (version.VersionArchivator, "/etc/fuel", "version"),
])
def test_dirs_archivator(mocker, cls, path, tag):
    test_archive = mocker.Mock()
    archive_mock = mocker.patch(
        "octane.handlers.backup_restore.base.archivate")
    cls(test_archive).backup()
    archive_mock.archive_dirs.assert_called_once_with(test_archive, path, tag)
