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
import json
import mock
import os
import pytest
import yaml

from keystoneclient.v2_0 import Client as keystoneclient

from octane.handlers.backup_restore import astute
from octane.handlers.backup_restore import cobbler
from octane.handlers.backup_restore import Context
from octane.handlers.backup_restore import fuel_keys
from octane.handlers.backup_restore import fuel_uuid
from octane.handlers.backup_restore import postgres
from octane.handlers.backup_restore import puppet
from octane.handlers.backup_restore import ssh
from octane.handlers.backup_restore import version
from octane.util import subprocess


class TestMember(object):

    def __init__(self, name, is_file, is_extractable):
        self.name = name
        self.is_file = is_file
        self.is_extractable = is_extractable
        self.path = ''
        self.is_extracted = False
        self.dump = ""

    def isfile(self):
        return self.is_file

    def assert_extract(self, path=None):
        assert self.is_extractable == self.is_extracted
        if self.is_extracted and path:
            assert os.path.join(path, "/") == os.path.join(self.path, "/")

    def read(self):
        return self.dump


class TestArchive(object):

    def __init__(self, members, foo):
        self.members = members
        for idx, member in enumerate(self.members):
            member.dump = "TestArchive_{0}_TestMember_{1}".format(
                foo.__name__, idx)

    def __iter__(self):
        return iter(self.members)

    def extract(self, member, path):
        member.path = path
        member.is_extracted = True

    def extractfile(self, name):
        for m in self.members:
            if m.name == name:
                m.is_extracted = True
                return m


@pytest.mark.parametrize("cls,path,members", [
    (
        ssh.SshArchivator,
        "/root/.ssh/",
        [
            ("ssh/", False, False),
            ("ssh/k1y", True, True),
            ("ssh/k1y123", True, True),
            ("ssh_old/k1y123", True, False),
        ],
    ),
    (
        fuel_keys.FuelKeysArchivator,
        "/var/lib/fuel/keys",
        [
            ("fuel_keys/", False, False),
            ("fuel_keys/nginx.crt", True, True),
            ("fuel_keys/1/nginx.key", True, True),
        ],
    ),
    (
        puppet.PuppetArchivator, "/etc/puppet", [
            ("puppet/", False, False),
            ("puppet/some_dir", False, False),
            ("puppet/some_dir/file_1", True, True),
            ("puppet/some_dir_2/file_1", True, True),
            ("puppet_1/some_dir_2/file_1", True, False),
        ]
    ),
    (
        version.VersionArchivator, "/etc/fuel", [
            ("version/", False, False),
            ("version/some_dir", False, False),
            ("version/some_dir/file_1", True, True),
            ("version/some_dir_2/file_1", True, True),
            ("version_1/some_dir_2/file_1", True, False),
        ]
    ),
    (
        fuel_uuid.FuelUUIDArchivator, "/etc/fuel/fuel-uuid", [
            ("fuel_uuid/fuel-uuid", True, True),
        ]
    ),
])
def test_path_restore(mocker, cls, path, members):
    members = [TestMember(n, f, e) for n, f, e in members]
    archive = TestArchive(members, cls)
    cls(archive).restore()
    for member in members:
        member.assert_extract(path)


@pytest.mark.parametrize("cls,path,container,members", [
    (
        cobbler.CobblerArchivator,
        "/var/lib/cobbler/config/systems.d/",
        "cobbler",
        [
            ("cobbler/file", True, True),
            ("cobbler/dir/file", True, True),
        ],
    ),
])
def test_container_archivator(mocker, cls, path, container, members):
    docker = mocker.patch("octane.util.docker.write_data_in_docker_file")
    members = [TestMember(n, f, e) for n, f, e in members]
    archive = TestArchive(members, cls)
    cls(archive).restore()
    for member in members:
        member.assert_extract()
        path_restor = member.name[len(container) + 1:]
        docker.assert_has_calls([
            mock.call(container, os.path.join(path, path_restor), member.dump)
        ])


@pytest.mark.parametrize("cls,db,sync_db_cmd", [
    (postgres.NailgunArchivator, "nailgun", ["nailgun_syncdb"]),
    (postgres.KeystoneArchivator, "keystone", ["keystone-manage", "db_sync"]),
])
def test_postgres_restore(mocker, cls, db, sync_db_cmd):
    member = TestMember("postgres/{0}.sql".format(db), True, True)
    archive = TestArchive([member], cls)
    actions = []

    def foo(action):
        return_mock_object = mocker.Mock()

        def mock_foo(*args, **kwargs):
            actions.append(action)
            return return_mock_object
        mock_foo.return_value = return_mock_object
        return mock_foo

    call_mock = mocker.patch("octane.util.subprocess.call",
                             side_effect=foo("call"))
    in_container_mock = mocker.patch("octane.util.docker.in_container")
    side_effect_in_container = foo("in_container")
    in_container_mock.return_value.__enter__.side_effect = \
        side_effect_in_container
    run_in_container = mocker.patch(
        "octane.util.docker.run_in_container",
        side_effect=foo("run_in_container"))
    mocker.patch("octane.util.docker.stop_container",
                 side_effect=foo("stop_container"))
    mocker.patch("octane.util.docker.start_container",
                 side_effect=foo("start_container"))
    cls(archive).restore()
    member.assert_extract()
    assert ["call", "stop_container", "run_in_container", "in_container",
            "call", "start_container"] == actions

    call_mock.assert_has_calls([
        mock.call(["systemctl", "stop", "docker-{0}.service".format(db)]),
        mock.call(["systemctl", "start", "docker-{0}.service".format(db)])
    ])
    in_container_mock.assert_called_once_with(
        "postgres",
        ["sudo", "-u", "postgres", "psql"],
        stdin=subprocess.PIPE
    )
    run_in_container.assert_has_calls([
        mock.call("postgres",
                  ["sudo", "-u", "postgres", "dropdb", "--if-exists", db]),
    ])
    side_effect_in_container.return_value.stdin.write.assert_called_once_with(
        member.dump)


@pytest.mark.parametrize("keys_in_dump_file,restored", [
    ([
        ("HOSTNAME", None),
        ("DNS_DOMAIN", None),
        ("DNS_SEARCH", None),
        ("DNS_UPSTREAM", None),
        ("ADMIN_NETWORK", [
            "interface",
            "ipaddress",
            "netmask",
            "dhcp_pool_start",
            "dhcp_pool_end",
            "dhcp_gateway",
        ]),
        ("astute", ["user", "password"]),
        ("cobbler", ["user", "password"]),
        ("keystone", [
            "admin_token",
            "ostf_user",
            "ostf_password",
            "nailgun_user",
            "nailgun_password",
            "monitord_user",
            "monitord_password",
        ]),
        ("mcollective", ["user", "password"]),
        ("postgres", [
            "keystone_dbname",
            "keystone_user",
            "keystone_password",
            "nailgun_dbname",
            "nailgun_user",
            "nailgun_password",
            "ostf_dbname",
            "ostf_user",
            "ostf_password",
        ]),
        ("FUEL_ACCESS", ["user", "password"]),
        ("KEY_NOT_FOR_RESTORE", None),
        ("SEQ_KEY_NOT_FOR_RESTORE", ["key_q", "key_w", "key_e"]),
    ], True),
    ([
        ("HOSTNAME", None),
        ("DNS_DOMAIN", None),
        ("DNS_SEARCH", None),
        ("DNS_UPSTREAM", None),
        ("ADMIN_NETWORK", [
            "interface",
            "dhcp_pool_start",
            "dhcp_pool_end",
            "dhcp_gateway",
        ]),
        ("astute", ["user", "password"]),
        ("cobbler", ["user", "password"]),
        ("keystone", [
            "admin_token",
            "ostf_user",
            "ostf_password",
            "nailgun_user",
            "nailgun_password",
            "monitord_user",
            "monitord_password",
        ]),
        ("mcollective", ["user", "password"]),
        ("postgres", [
            "keystone_dbname",
            "keystone_user",
            "keystone_password",
            "nailgun_dbname",
            "nailgun_user",
            "nailgun_password",
            "ostf_dbname",
            "ostf_user",
            "ostf_password",
        ]),
        ("FUEL_ACCESS", ["user", "password"]),
        ("KEY_NOT_FOR_RESTORE", None),
        ("SEQ_KEY_NOT_FOR_RESTORE", ["key_q", "key_w", "key_e"]),
    ], False),
    ([], False),
])
def test_astute_restore(mocker, mock_open, keys_in_dump_file, restored):
    required_keys = dict([
        ("HOSTNAME", None),
        ("DNS_DOMAIN", None),
        ("DNS_SEARCH", None),
        ("DNS_UPSTREAM", None),
        ("ADMIN_NETWORK", [
            "interface",
            "ipaddress",
            "netmask",
            "dhcp_pool_start",
            "dhcp_pool_end",
            "dhcp_gateway",
        ]),
        ("astute", ["user", "password"]),
        ("cobbler", ["user", "password"]),
        ("keystone", [
            "admin_token",
            "ostf_user",
            "ostf_password",
            "nailgun_user",
            "nailgun_password",
            "monitord_user",
            "monitord_password",
        ]),
        ("mcollective", ["user", "password"]),
        ("postgres", [
            "keystone_dbname",
            "keystone_user",
            "keystone_password",
            "nailgun_dbname",
            "nailgun_user",
            "nailgun_password",
            "ostf_dbname",
            "ostf_user",
            "ostf_password",
        ]),
        ("FUEL_ACCESS", ["user", "password"]),
    ])

    astute_name = "astute/astute.yaml"
    member = TestMember(astute_name, True, True)
    member.dump = ""
    dump_dict = {}
    current_dict = {}
    dict_to_restore = {}
    for key, seq in keys_in_dump_file:
        if seq is None:
            dump_dict[key] = "dump_val"
            current_dict[key] = "current_val"
        else:
            dump_dict[key] = dict((s, "dump_val") for s in seq)
            current_dict[key] = dict((s, "current_val") for s in seq)
        if key in required_keys:
            dict_to_restore[key] = dump_dict[key]
        else:
            dict_to_restore[key] = current_dict[key]

    mocker.patch("yaml.load", side_effect=[dump_dict, current_dict])
    safe_dump = mocker.patch("yaml.safe_dump")
    copy_mock = mocker.patch("shutil.copy")
    move_mock = mocker.patch("shutil.move")
    cls = astute.AstuteArchivator
    archive = TestArchive([member], cls)
    try:
        cls(archive).restore()
    except Exception as exc:
        if restored:
            raise
        assert str(exc).startswith("Not found values in backup for keys: ")
    else:
        assert restored
        member.assert_extract()
        copy_mock.assert_called_once_with(
            "/etc/fuel/astute.yaml", "/etc/fuel/astute.yaml.old")
        move_mock.assert_called_once_with(
            "/etc/fuel/astute.yaml.new", "/etc/fuel/astute.yaml")
        safe_dump.assert_called_once_with(dict_to_restore,
                                          mock_open.return_value,
                                          default_flow_style=False)


def test_post_restore_action_astute(mocker):

    stopped = []
    mocker.patch(
        "octane.util.docker.get_docker_container_names",
        return_value=["container_1", "container_2"]
    )
    start = mocker.patch("octane.util.docker.start_container",
                         side_effect=stopped.remove)
    stop = mocker.patch("octane.util.docker.stop_container",
                        side_effect=stopped.append)
    puppet = mocker.patch("octane.util.puppet.apply_host")

    astute.AstuteArchivator(None).post_restore_action()
    assert start.called
    assert stop.called
    assert puppet.called
    assert not stopped


def test_post_restore_nailgun(mocker):
    data = yaml.dump([
        {"fields": {"k": 1, "p": 2}},
        {"fields": {}},
        {"fields": {"k": 3}},
    ])

    mocker.patch("octane.util.docker.run_in_container",
                 return_value=(data, None))
    token = "123"

    def mock_init(self, *args, **kwargs):
        self.auth_token = token

    mocker.patch.object(keystoneclient, "__init__", mock_init)
    post_data = mocker.patch("requests.post")
    postgres.NailgunArchivator(None).post_restore_action(
        Context(password="pwd"))

    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }
    post_url = 'http://127.0.0.1:8000/api/v1/releases/'
    post_data.assert_has_calls(
        [
            mock.call(post_url, json.dumps({"p": 2, "k": 1}), headers=headers),
            mock.call(post_url, json.dumps({"p": 2, "k": 3}), headers=headers),
        ],
        any_order=True
    )
