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
import yaml

from keystoneclient.v2_0 import Client as keystoneclient

from octane.handlers import backup_restore
from octane.handlers.backup_restore import astute
from octane.handlers.backup_restore import cobbler
from octane.handlers.backup_restore import fuel_keys
from octane.handlers.backup_restore import fuel_uuid
from octane.handlers.backup_restore import logs
from octane.handlers.backup_restore import mirrors
from octane.handlers.backup_restore import postgres
from octane.handlers.backup_restore import puppet
from octane.handlers.backup_restore import release
from octane.handlers.backup_restore import ssh
from octane.handlers.backup_restore import version
from octane import magic_consts
from octane.util import subprocess


class TestMember(object):

    def __init__(self, name, is_file, is_extractable):
        self.name = name
        self.is_file = is_file
        self.is_extractable = is_extractable
        self.path = ''
        self.is_extracted = False
        self.dump = ""
        self.read_idx = 0

    def isfile(self):
        return self.is_file

    def assert_extract(self, path=None):
        assert self.is_extractable == self.is_extracted
        if self.is_extracted and path:
            assert os.path.join(path, "/") == os.path.join(self.path, "/")

    def read(self, chunk_size=None):
        current_idx = self.read_idx
        if chunk_size:
            self.read_idx += chunk_size
        else:
            self.read_idx = len(self.dump)
        return self.dump[current_idx: self.read_idx]


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
    (
        mirrors.MirrorsBackup,
        "/var/www/nailgun/",
        [
            ("mirrors/", False, False),
            ("mirrors/data.txt", True, True),
            ("mirrors/subdir/data.txt", True, True),
        ],
    ),
    (
        mirrors.RepoBackup,
        "/var/www/nailgun/",
        [
            ("repos/", False, False),
            ("repos/data.txt", True, True),
            ("repos/subdir/data.txt", True, True),
        ],
    ),
])
def test_path_restore(mocker, cls, path, members):
    subprocess_mock = mocker.patch("octane.util.subprocess.call")
    members = [TestMember(n, f, e) for n, f, e in members]
    archive = TestArchive(members, cls)
    mocker.patch("os.environ", new_callable=mock.PropertyMock(return_value={}))
    cls(
        archive, backup_restore.NailgunCredentialsContext('user', 'password')
    ).restore()
    for member in members:
        member.assert_extract(path)
    if cls is ssh.SshArchivator:
        subprocess_mock.assert_called_once_with(
            ["fuel-bootstrap", "build", "--activate"],
            env={'KEYSTONE_PASS': 'password', 'KEYSTONE_USER': 'user'})
    else:
        assert not subprocess_mock.called


@pytest.mark.parametrize("cls,path,backup_name,members", [
    (
        cobbler.CobblerSystemArchivator,
        "/var/lib/cobbler/config/systems.d/",
        "cobbler",
        [
            ("cobbler/file", True, True),
            ("cobbler/dir/file", True, True),
        ],
    ),
    (
        cobbler.CobblerDistroArchivator,
        "/var/lib/cobbler/config/distros.d/",
        "cobbler_distros",
        [
            ("cobbler_distros/file", True, True),
            ("cobbler_distros/dir/file", True, True),
        ],
    ),
    (
        cobbler.CobblerProfileArchivator,
        "/var/lib/cobbler/config/profiles.d/",
        "cobbler_profiles",
        [
            ("cobbler_profiles/file", True, True),
            ("cobbler_profiles/dir/file", True, True),
        ],
    ),
])
def test_path_filter_restore(mocker, cls, path, backup_name, members):
    members = [TestMember(n, f, e) for n, f, e in members]
    archive = TestArchive(members, cls)
    cls(archive).restore()
    for member in members:
        member.assert_extract()


@pytest.mark.parametrize("cls,db,sync_db_cmd,mocked_actions_names", [
    (
        postgres.NailgunArchivator,
        "nailgun",
        ["nailgun_syncdb"],
        ["_repair_database_consistency"],
    ),
    (
        postgres.KeystoneArchivator,
        "keystone",
        ["keystone-manage", "db_sync"],
        [],
    ),
])
def test_postgres_restore(mocker, cls, db, sync_db_cmd, mocked_actions_names):
    patch_mock = mocker.patch("octane.util.docker.apply_patches")
    mocked_actions = []
    for mocked_action_name in mocked_actions_names:
        mocked_actions.append(mocker.patch.object(cls, mocked_action_name))
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
    mocker.patch("octane.util.docker.wait_for_container",
                 side_effect=foo("wait_for_container"))
    cls(archive).restore()
    member.assert_extract()
    args = ["call", "stop_container", "run_in_container", "in_container",
            "start_container", "wait_for_container", "call"]
    assert args == actions
    if cls is postgres.NailgunArchivator:
        assert [
            mock.call(
                'nailgun',
                '/etc/puppet/modules/nailgun/manifests/',
                os.path.join(magic_consts.CWD, "patches/timeout.patch")
            ),
            mock.call(
                'nailgun',
                '/etc/puppet/modules/nailgun/manifests/',
                os.path.join(magic_consts.CWD, "patches/timeout.patch"),
                revert=True
            ),
        ] == patch_mock.call_args_list
    else:
        assert not patch_mock.called

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
    for mocked_action in mocked_actions:
        mocked_action.assert_called_once_with()


@pytest.mark.parametrize("keys_in_dump_file,restored", [
    ([
        ("HOSTNAME", None),
        ("DNS_DOMAIN", None),
        ("DNS_SEARCH", None),
        ("DNS_UPSTREAM", None),
        ("ADMIN_NETWORK", [
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
            dump_dict[key] = {s: "dump_val" for s in seq}
            current_dict[key] = {s: "current_val" for s in seq}
        if key in required_keys:
            dict_to_restore[key] = dump_dict[key]
        else:
            dict_to_restore[key] = current_dict[key]

    mocker.patch("yaml.load", side_effect=[dump_dict, current_dict])
    safe_dump = mocker.patch("yaml.safe_dump")
    copy_mock = mocker.patch("shutil.copy2")
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


@pytest.mark.parametrize(("dump", "calls"), [
    (
        [{"fields": {"k": 1, "p": 2}}, {"fields": {}}, {"fields": {"k": 3}}],
        [{"p": 2, "k": 1}, {"p": 2, "k": 3}],
    ),
    (
        [
            {"fields": {"k": 1, "p": 2, "c": {"k": 1, "p": {"a": 1}}}},
            {"fields": {}},
            {"fields": {"k": 3, "c": {"k": 3, "p": {"c": 4}}}},
        ],
        [
            {"p": 2, "c": {"p": {"a": 1}, "k": 1}, "k": 1},
            {'p': 2, 'c': {'p': {'a': 1, 'c': 4}, 'k': 3}, 'k': 3},
        ],
    ),
])
def test_release_restore(mocker, mock_open, dump, calls):
    data = yaml.dump(dump)
    mock_subprocess_call = mocker.patch("octane.util.subprocess.call")
    run_in_container_mock = mocker.patch(
        "octane.util.docker.run_in_container", return_value=(data, None))
    json_mock = mocker.patch("json.dumps")
    token = "123"

    def mock_init(self, *args, **kwargs):
        self.auth_token = token

    mocker.patch.object(keystoneclient, "__init__", mock_init)
    post_data = mocker.patch("requests.post")
    mocker.patch("os.environ", new_callable=mock.PropertyMock(return_value={}))
    release.ReleaseArchivator(
        None,
        backup_restore.NailgunCredentialsContext(
            user="admin", password="password")
    ).restore()

    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }
    post_url = 'http://127.0.0.1:8000/api/v1/releases/'
    post_call = mock.call(post_url, json_mock.return_value, headers=headers)
    for call in post_data.call_args_list:
        assert post_call == call
    json_mock.assert_has_calls([mock.call(d) for d in calls], any_order=True)
    assert json_mock.call_count == 2
    mock_subprocess_call.assert_called_once_with([
        "fuel", "release", "--sync-deployment-tasks", "--dir", "/etc/puppet/"],
        env={'KEYSTONE_PASS': 'password', 'KEYSTONE_USER': 'admin'}
    )

    run_in_container_mock.assert_called_once_with(
        "nailgun",
        ["cat", magic_consts.OPENSTACK_FIXTURES],
        stdout=subprocess.PIPE
    )


def test_repair_database_consistency(mocker, mock_open):
    run_sql_mock = mocker.patch(
        "octane.util.sql.run_psql_in_container",
        return_value=["1|{}"],
    )
    json_mock = mocker.patch("json.dumps")

    mocker.patch("os.environ", new_callable=mock.PropertyMock(return_value={}))
    context = backup_restore.NailgunCredentialsContext(
        user="admin", password="password")
    archivator = postgres.NailgunArchivator(None, context)
    archivator._repair_database_consistency()

    json_mock.assert_called_once_with({"deployed_before": {"value": True}})
    run_sql_mock.assert_has_calls([
        mock.call("select id, generated from attributes;", "nailgun"),
    ])


def test_post_restore_puppet_apply_host(mocker):
    context = backup_restore.NailgunCredentialsContext(
        user="admin", password="user_pswd")
    mock_set_astute_password = mocker.patch(
        "octane.util.auth.set_astute_password")
    mock_apply = mocker.patch("octane.util.puppet.apply_host")

    archivator = puppet.PuppetApplyHost(None, context)
    archivator.restore()

    assert mock_apply.called
    mock_set_astute_password.assert_called_once_with(context)


@pytest.mark.parametrize("nodes", [
    [("node_1", True), ("node_2", True), ("node_3", True)],
    [("node_1", False)],
    [("node_1", False), ("node_2", False), ("node_3", False)],
    [("node_1", False), ("node_2", True), ("node_3", False)],
])
@pytest.mark.parametrize("is_dir", [True, False])
@pytest.mark.parametrize("exception", [True, False])
def test_logs_restore(mocker, mock_open, nodes, is_dir, exception):
    domain_name = "test_domain"
    mocker.patch("yaml.load", return_value={"DNS_DOMAIN": domain_name})
    domain_names = []
    fuel_client_values = []
    is_link_exists = []
    moved_nodes = []
    for idx, node_link_exits in enumerate(nodes):
        node, link_exists = node_link_exits
        node_domain_name = "{0}.{1}".format(node, domain_name)
        domain_names.append(node_domain_name)
        ip_addr = "10.21.10.{0}".format(idx + 1)
        fuel_client_mock = mocker.Mock()
        fuel_client_mock.data = {
            "meta": {
                "system": {
                    "fqdn": node_domain_name
                }
            },
            "ip": ip_addr,
        }
        fuel_client_values.append(fuel_client_mock)
        is_link_exists.append(link_exists)
        if not link_exists:
            moved_nodes.append((node_domain_name, ip_addr))
    is_link_mock = mocker.patch("os.path.islink", side_effect=is_link_exists)
    mocker.patch("os.path.isdir", return_value=is_dir)
    mocker.patch("fuelclient.objects.Node.get_all",
                 return_value=fuel_client_values)
    run_in_container_mock = mocker.patch(
        "octane.util.docker.run_in_container")
    rename_mock = mocker.patch("os.rename")
    symlink_mock = mocker.patch("os.symlink")
    mkdir_mock = mocker.patch("os.mkdir")
    context = backup_restore.NailgunCredentialsContext(
        user="admin", password="user_pswd")
    archivator = logs.LogsArchivator(None, context)
    if not exception:

        class TestException(Exception):
            pass

        is_link_mock.side_effect = TestException("test exc")
        with pytest.raises(TestException):
            archivator.restore()
        assert not mkdir_mock.called
        assert not rename_mock.called
    else:
        archivator.restore()
        path = "/var/log/docker-logs/remote/"
        path_pairs = [(os.path.join(path, d), os.path.join(path, i))
                      for d, i in moved_nodes]
        sym_calls = [mock.call(d, os.path.join(path, i))
                     for d, i in moved_nodes]
        if is_dir:
            assert [mock.call(i, d) for d, i in path_pairs] == \
                rename_mock.call_args_list
            assert not mkdir_mock.called
        else:
            assert [mock.call(d) for d, _ in path_pairs] == \
                mkdir_mock.call_args_list
            assert not rename_mock.called
        assert sym_calls == symlink_mock.call_args_list
    assert [mock.call("rsyslog", ["service", "rsyslog", "stop"]),
            mock.call("rsyslog", ["service", "rsyslog", "start"])] == \
        run_in_container_mock.call_args_list
