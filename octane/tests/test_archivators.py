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
import os
import pytest

from octane.handlers.backup_restore import admin_networks
from octane.handlers.backup_restore import astute
from octane.handlers.backup_restore import base
from octane.handlers.backup_restore import cobbler
from octane.handlers.backup_restore import fuel_keys
from octane.handlers.backup_restore import fuel_uuid
from octane.handlers.backup_restore import mirrors
from octane.handlers.backup_restore import nailgun_plugins
from octane.handlers.backup_restore import postgres
from octane.handlers.backup_restore import puppet
from octane.handlers.backup_restore import ssh
from octane.handlers.backup_restore import version


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
    "cls,banned_files,backup_directory,allowed_files,backup_name", [
        (
            cobbler.CobblerSystemArchivator,
            ["default.json"],
            "/var/lib/cobbler/config/systems.d/",
            None,
            "cobbler",
        ),
        (
            cobbler.CobblerProfileArchivator,
            ["bootstrap.json", "ubuntu_bootstrap.json"],
            "/var/lib/cobbler/config/profiles.d/",
            None,
            "cobbler_profiles",
        ),
        (
            cobbler.CobblerDistroArchivator,
            ["bootstrap.json", "ubuntu_bootstrap.json"],
            "/var/lib/cobbler/config/distros.d/",
            None,
            "cobbler_distros",
        ),
        (
            admin_networks.AdminNetworks,
            [],
            "/etc/hiera/networks.yaml",
            ["networks.yaml"],
            "networks"
        ),
    ])
def test_path_filter_backup(mocker, cls, banned_files, backup_directory,
                            allowed_files, backup_name):
    def foo(path, path_in_archive):
        assert path.startswith(backup_directory)
        assert path_in_archive.startswith(backup_name)
        filename = path[len(backup_directory):].lstrip(os.path.sep)
        filename_in_archive = \
            path_in_archive[len(backup_name):].lstrip(os.path.sep)
        assert filename == filename_in_archive
        backuped_files.add(filename)

    filenames = banned_files + (allowed_files or []) + ["tmp1", "tmp2"]
    files_to_archive = filenames
    if allowed_files:
        files_to_archive = [d for d in files_to_archive if d in allowed_files]
    files_to_archive = [d for d in files_to_archive if d not in banned_files]
    backuped_files = set()

    test_archive = mocker.Mock()
    test_archive.add.side_effect = foo

    mock_os_walk = mocker.patch("os.walk")
    mock_os_walk.return_value = [(backup_directory, (), filenames)]

    cls(test_archive).backup()

    mock_os_walk.assert_called_once_with(backup_directory)

    for filename in files_to_archive:
        assert filename in backuped_files
    for filename in set(filenames) - set(files_to_archive):
        assert filename not in backuped_files


@pytest.mark.parametrize("cls,db", [
    (postgres.NailgunArchivator, "nailgun"),
    (postgres.KeystoneArchivator, "keystone"),
])
def test_posgres_archivator(mocker, cls, db):
    test_archive = mocker.Mock()
    archive_mock = mocker.patch(
        "octane.util.archivate.archivate_cmd_output")
    cls(test_archive).backup()
    archive_mock.assert_called_once_with(
        test_archive,
        ["sudo", "-u", "postgres", "pg_dump", "-C", db],
        "postgres/{0}.sql".format(db))


@pytest.mark.parametrize("cls, path, tag", [
    (puppet.PuppetArchivator, "/etc/puppet", "puppet"),
    (version.VersionArchivator, "/etc/fuel", "version"),
])
def test_dirs_archivator(mocker, cls, path, tag):
    test_archive = mocker.Mock()
    archive_mock = mocker.patch("octane.util.archivate.archive_dirs")
    cls(test_archive).backup()
    archive_mock.assert_called_once_with(test_archive, path, tag)


@pytest.mark.parametrize("path_exists", [(True,), (False,)])
def test_nailgun_plugins_backup(mocker, path_exists):
    test_archive = mocker.Mock()
    path = "/var/www/nailgun/plugins"
    name = "nailgun_plugins"
    path_exists_mock = mocker.patch("os.path.exists", return_value=path_exists)
    nailgun_plugins.NailgunPluginsArchivator(test_archive).backup()
    path_exists_mock.assert_called_once_with(path)
    if path_exists:
        test_archive.add.assert_called_once_with(path, name)
    else:
        assert not test_archive.add.called


@pytest.mark.parametrize(
    "cls, name, ipaddr, attributes, archive_add_list",
    [
        (
            mirrors.MirrorsBackup,
            "mirrors",
            "127.0.0.1",
            [
                {"repo_setup": {"repos": {"value": [
                    {"uri": "http://127.0.0.1:8080/test_fest"},
                    {"uri": "http://127.0.0.1:8080/test_fest"},
                    {"uri": "http://127.0.0.1:8080/test_fest_2"}
                ]}}}
            ],
            ["test_fest", "test_fest_2"]
        ),
        (
            mirrors.MirrorsBackup,
            "mirrors",
            "127.0.0.1",
            [
                {"repo_setup": {"repos": {"value": [
                    {"uri": "http://127.0.0.1:8080/test_fest"},
                    {"uri": "http://127.0.0.1:8080/test_fest"},
                    {"uri": "http://127.0.0.1:8080/test_fest_2"}
                ]}}},
                {"repo_setup": {"repos": {"value": [
                    {"uri": "http://127.0.0.1:8080/test_fest"},
                    {"uri": "http://127.0.0.1:8080/test_fest_3"},
                    {"uri": "http://127.0.0.1:8080/test_fest_2"}
                ]}}},
            ],
            ["test_fest", "test_fest_2", "test_fest_3"]
        ),
        (
            mirrors.MirrorsBackup,
            "mirrors",
            "127.0.0.1",
            '',
            []
        ),
        (
            mirrors.RepoBackup,
            "repos",
            "127.0.0.1",
            [
                {"provision": {"image_data": {
                    "1": {"uri": "http://127.0.0.1:8080/test_fest"},
                    "2": {"uri": "http://127.0.0.1:8080/test_fest_2"},
                    "3": {"uri": "http://127.0.0.1:8080/test_fest_3"},
                    "4": {"uri": "http://127.0.0.1:8080/test_fest_5"}
                }}}
            ],
            ['test_fest', 'test_fest_2', 'test_fest_3', "test_fest_5"]
        ),
        (
            mirrors.RepoBackup,
            "repos",
            "127.0.0.1",
            [
                {"provision": {"image_data": {
                    "1": {"uri": "http://127.0.0.1:8080/test_fest"},
                    "2": {"uri": "http://127.0.0.1:8080/test_fest_2"},
                    "3": {"uri": "http://127.0.0.1:8080/test_fest_3"},
                    "4": {"uri": "http://127.0.0.1:8080/test_fest"}
                }}},
                {"provision": {"image_data": {
                    "1": {"uri": "http://127.0.0.1:8080/test_fest"},
                    "2": {"uri": "http://127.0.0.1:8080/test_fest_2"},
                    "3": {"uri": "http://127.0.0.1:8080/test_fest_3"},
                    "4": {"uri": "http://127.0.0.1:8080/test_fest_5"}
                }}},
            ],
            ['test_fest', 'test_fest_2', 'test_fest_3', "test_fest_5"]
        ),
        (
            mirrors.RepoBackup,
            "repos",
            "127.0.0.1",
            [],
            []
        ),
    ]
)
def test_repos_backup(
        mocker, mock_open, cls, name, ipaddr,
        attributes, archive_add_list):
    yaml_mocker = mocker.patch(
        "yaml.load",
        return_value={"ADMIN_NETWORK": {"ipaddress": "127.0.0.1"}})
    mocker.patch.object(cls, '_get_attributes', return_value=attributes)

    test_archive = mocker.Mock()
    path = "/var/www/nailgun/"

    cls(test_archive).backup()
    yaml_mocker.assert_called_once_with(mock_open.return_value)

    test_archive.add.assert_has_calls(
        [
            mock.call(os.path.join(path, i), os.path.join(name, i))
            for i in archive_add_list
        ],
        any_order=True)
    assert test_archive.add.call_count == len(archive_add_list)


# @pytest.mark.parametrize("cls,path,name", [
#     (
#         admin_networks.AdminNetworks,
#         "/etc/hiera/networks.yaml",
#         "networks/networks.yaml"
#     )
# ])
# @pytest.mark.parametrize("is_exists", [True, False])
# def test_admin_networks_backup(mocker, cls, path, name, is_exists):
#     test_archive = mocker.Mock()
#     mock_exists = mocker.patch("os.path.exists", return_value=is_exists)
#     cls(test_archive).backup()
#     mock_exists.assert_called_once_with(path)
#     if is_exists:
#         test_archive.add.assert_called_once_with(path, name)


@pytest.mark.parametrize("name, expected_name", [
    ("TestArchivator", "test"),
    ("TestBackup", "test"),
    ("Test", "test"),
    ("NotTestArchivator", "not test"),
    ("NewBornTestCase", "new born test case"),
])
def test_archivator_name(mocker, name, expected_name):

    assert expected_name == type(name, (base.Base, ), {})(None).archivator_name
