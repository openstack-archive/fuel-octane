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
import io
import mock
import os
import pytest

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
            env={'OS_PASSWORD': 'password', 'OS_USERNAME': 'user'})
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


def test_cobbler_archivator(mocker, mock_subprocess):
    mocker.patch.object(cobbler.CobblerSystemArchivator, "restore")
    mocker.patch.object(cobbler.CobblerDistroArchivator, "restore")
    mocker.patch.object(cobbler.CobblerProfileArchivator, "restore")
    mock_puppet = mocker.patch("octane.util.puppet.apply_task")
    cobbler.CobblerArchivator(mock.Mock(), mock.Mock()).restore()
    mock_subprocess.assert_called_once_with(
        ["systemctl", "stop", "cobblerd"])
    mock_puppet.assert_called_once_with("cobbler")


def test_databases_archivator(mocker):
    mock_call = mock.Mock()
    mocker.patch.object(postgres.NailgunArchivator, "restore",
                        new=mock_call.nailgun.restore)
    mocker.patch.object(postgres.KeystoneArchivator, "restore",
                        new=mock_call.keystone.restore)
    mocker.patch("octane.util.puppet.apply_task",
                 new=mock_call.puppet.apply_task)

    archivator = postgres.DatabasesArchivator(mock.Mock(), mock.Mock())
    archivator.restore()

    assert mock_call.mock_calls == [
        mock.call.puppet.apply_task("postgresql"),
        mock.call.keystone.restore(),
        mock.call.nailgun.restore(),
    ]


@pytest.mark.parametrize("cls,db,services", [
    (
        postgres.NailgunArchivator,
        "nailgun",
        [
            "nailgun",
            "oswl_flavor_collectord",
            "oswl_image_collectord",
            "oswl_keystone_user_collectord",
            "oswl_tenant_collectord",
            "oswl_vm_collectord",
            "oswl_volume_collectord",
            "receiverd",
            "statsenderd",
            "assassind",
        ],
    ),
    (
        postgres.KeystoneArchivator,
        "keystone",
        ["openstack-keystone"],
    ),
])
def test_postgres_restore(mocker, cls, db, services):
    member = TestMember("postgres/{0}.sql".format(db), True, True)
    archive = TestArchive([member], cls)

    mock_keystone = mock.Mock()
    mocker.patch("octane.util.keystone.unset_default_domain_id",
                 new=mock_keystone.unset)
    mocker.patch("octane.util.keystone.add_admin_token_auth",
                 new=mock_keystone.add)

    mock_subprocess = mock.MagicMock()
    mocker.patch("octane.util.subprocess.call", new=mock_subprocess.call)
    mocker.patch("octane.util.subprocess.popen", new=mock_subprocess.popen)

    mock_patch = mocker.patch("octane.util.patch.applied_patch")
    mock_copyfileobj = mocker.patch("shutil.copyfileobj")
    mock_set_astute_password = mocker.patch(
        "octane.util.auth.set_astute_password")
    mock_apply_task = mocker.patch("octane.util.puppet.apply_task")
    mock_context = mock.Mock()

    cls(archive, mock_context).restore()
    member.assert_extract()

    assert mock_subprocess.mock_calls == [
        mock.call.call(["systemctl", "stop"] + services),
        mock.call.call(["sudo", "-u", "postgres", "dropdb", "--if-exists",
                        db]),
        mock.call.popen(["sudo", "-u", "postgres", "psql"],
                        stdin=subprocess.PIPE),
        mock.call.popen().__enter__(),
        mock.call.popen().__exit__(None, None, None),
    ]
    mock_copyfileobj.assert_called_once_with(
        member,
        mock_subprocess.popen.return_value.__enter__.return_value.stdin,
    )
    mock_apply_task.assert_called_once_with(db)

    if cls is postgres.NailgunArchivator:
        assert mock_patch.call_args_list == [
            mock.call(
                '/etc/puppet/modules',
                os.path.join(magic_consts.CWD, "patches/timeout.patch"),
            ),
        ]
        assert not mock_keystone.called
    else:
        assert not mock_patch.called
        assert mock_keystone.mock_calls == [
            mock.call.unset("/etc/keystone/keystone.conf"),
            mock.call.add("/etc/keystone/keystone-paste.ini", [
                "pipeline:public_api",
                "pipeline:admin_api",
                "pipeline:api_v3",
            ]),
        ]
    mock_set_astute_password.assert_called_once_with(mock_context)


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
    mock_puppet = mocker.patch("octane.util.puppet.apply_task")
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
        assert mock_puppet.mock_calls == [
            mock.call("hiera"),
            mock.call("host"),
        ]


FAKE_OPENSTACK_YAML = """\
---
- &base_release
  fields: {"k": 0, "p": 2}
- pk: 1
  extend: *base_release
  fields: {"version": 1, "name": "first", "k": 1}
- &release2
  pk: 2
  extend: *base_release
  fields: {"version": 1, "name": "second", "k": 2}
- pk: 3
  extend: *release2
  fields: {"name": "third", "p": 3}
"""


@pytest.mark.parametrize(("content", "existing_releases", "calls"), [
    (
        FAKE_OPENSTACK_YAML,

        [{"version": 1, "name": "second"}],

        [{"version": 1, "name": "first", "k": 1, "p": 2},
         {"version": 1, "name": "third", "k": 2, "p": 3}],
    ),
])
def test_release_restore(mocker, mock_open, content, existing_releases, calls):
    mock_open.return_value = io.BytesIO(content)
    mock_subprocess_call = mocker.patch("octane.util.subprocess.call")
    fake_token = "123"

    def mock_init(self, *args, **kwargs):
        self.auth_token = fake_token

    mocker.patch.object(keystoneclient, "__init__", mock_init)
    mock_request = mocker.patch("requests.request")
    mock_request.return_value.json.return_value = existing_releases
    mocker.patch("os.environ", new_callable=mock.PropertyMock(return_value={}))

    release.ReleaseArchivator(
        None,
        backup_restore.NailgunCredentialsContext(
            user="admin", password="password")
    ).restore()

    headers = {
        "X-Auth-Token": fake_token,
        "Content-Type": "application/json"
    }
    url = 'http://127.0.0.1:8000/api/v1/releases/'
    expected_calls = [
        mock.call("GET", url, json=None, headers=headers)
    ] + [
        mock.call("POST", url, json=call, headers=headers)
        for call in calls
    ]
    assert mock_request.call_args_list == expected_calls
    mock_subprocess_call.assert_called_once_with([
        "fuel", "release", "--sync-deployment-tasks", "--dir", "/etc/puppet/"],
        env={'OS_PASSWORD': 'password', 'OS_USERNAME': 'admin'}
    )
    mock_open.assert_called_once_with(magic_consts.OPENSTACK_FIXTURES)


def test_post_restore_puppet_apply_tasks(mocker, mock_subprocess):
    context = backup_restore.NailgunCredentialsContext(
        user="admin", password="user_pswd")
    mock_set_astute_password = mocker.patch(
        "octane.util.auth.set_astute_password")
    mock_apply = mocker.patch("octane.util.puppet.apply_all_tasks")

    archivator = puppet.PuppetApplyTasks(None, context)
    archivator.restore()

    mock_subprocess.assert_called_once_with(["systemctl", "stop", "ostf"])
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
def test_logs_restore(
        mocker, mock_open, mock_subprocess, nodes, is_dir, exception):
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
        path = "/var/log/remote/"
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
    assert mock_subprocess.call_args_list == [
        mock.call(["systemctl", "stop", "rsyslog"]),
        mock.call(["systemctl", "start", "rsyslog"]),
    ]
