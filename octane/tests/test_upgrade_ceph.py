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

from octane.commands import upgrade_ceph
from octane.handlers.upgrade import ceph_osd


def test_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.upgrade_ceph.upgrade_ceph')
    octane_app.run(["upgrade-ceph", "1", "2"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, 2)


@pytest.mark.parametrize("env_node_ids", [
    # [(env_id, node_id), ... ]
    [(1, 1)],
    [(1, 1), (1, 2)],
    [(1, 1), (2, 2)]
    ])
def test_patch_and_revert_only_once(mocker, env_node_ids):
    patch_mock = mocker.patch("octane.util.puppet.patch_modules")
    mocker.patch("octane.util.ceph.check_cluster")
    mocker.patch("octane.util.node.preserve_partition")
    set_ceph_noout_mock = mocker.patch("octane.util.ceph.set_osd_noout")
    unset_ceph_noout_mock = mocker.patch("octane.util.ceph.unset_osd_noout")
    handlers = []
    envs = {}
    for env_id, node_id in env_node_ids:
        try:
            env = envs[env_id]
        except KeyError:
            env = mock.Mock()
            env.data = {
                "id": env_id,
                "fuel_version": "xxx"
            }
            envs[env_id] = env
        node = mock.Mock()
        node.env = env
        node.data = {"id": node_id}
        handlers.append(ceph_osd.CephOsdUpgrade(node, env, False, False))
    for handler in handlers:
        handler.preupgrade()
    for handler in handlers:
        handler.prepare()
    for handler in handlers:
        handler.postdeploy()
    assert [mock.call(), mock.call(revert=True)] == patch_mock.call_args_list
    env_calls = [mock.call(e) for e in envs.values()]
    assert env_calls == set_ceph_noout_mock.call_args_list
    assert env_calls == unset_ceph_noout_mock.call_args_list


CEPH_CONF_BASE = "key = value\n"
CEPH_CONF_KEYRING = CEPH_CONF_BASE + "[client.radosgw.gateway]\n"
CEPH_CONF_RGWFRONT = CEPH_CONF_KEYRING + \
    "rgw_frontends = fastcgi socket_port=9000 socket_host=127.0.0.1\n"


@pytest.mark.parametrize("conf,expected_res", [
    (CEPH_CONF_BASE, CEPH_CONF_BASE),
    (CEPH_CONF_KEYRING, CEPH_CONF_RGWFRONT),
    (CEPH_CONF_RGWFRONT, CEPH_CONF_RGWFRONT),
])
def test_add_rgw_frontends(mocker, conf, expected_res):
    assert expected_res == upgrade_ceph.add_rgw_frontends(conf)


@pytest.mark.parametrize("fsid", ["fsid_value"])
@pytest.mark.parametrize("conf_file", ["/conf/file/path"])
@pytest.mark.parametrize("edit_conf,expected_conf", [(
    [
        "[global]\n",
        "fsid = 2f496dc5-f9df-4c03-9dd6-f7dd5997bd4b\n",
        "mon_initial_members = node-1 node-3 node-2\n",
        "mon_host = 10.21.7.3 10.21.7.5 10.21.7.4\n",
        "auth_cluster_required = cephx\n",
        "auth_service_required = cephx\n",
        "auth_client_required = cephx\n",
        "filestore_xattr_use_omap = true\n",
        "log_to_syslog_level = info\n",
        "log_to_syslog = True\n",
        "osd_pool_default_size = 2\n",
        "osd_pool_default_min_size = 1\n",
        "log_file = /var/log/ceph/radosgw.log\n",
        "osd_pool_default_pg_num = 128\n",
        "public_network = 10.21.7.0/24\n",
        "log_to_syslog_facility = LOG_LOCAL0\n",
        "osd_journal_size = 2048\n",
        "auth_supported = cephx\n",
        "osd_pool_default_pgp_num = 128\n",
        "osd_mkfs_type = xfs\n",
        "cluster_network = 10.21.9.0/24\n",
        "osd_recovery_max_active = 1\n",
        "osd_max_backfills = 1\n",
        "\n",
        "\n",
        "[client]\n",
        "rbd cache writethrough until flush = True\n",
        "rbd cache = True\n",
        "rbd_cache_writethrough_until_flush = True\n",
        "rbd_cache = True",
    ],
    [

        "[global]\n",
        "fsid = {fsid_value}\n",
        "mon_initial_members = node-1 node-3 node-2\n",
        "mon_host = 10.21.7.3 10.21.7.5 10.21.7.4\n",
        "auth_cluster_required = cephx\n",
        "auth_service_required = cephx\n",
        "auth_client_required = cephx\n",
        "filestore_xattr_use_omap = true\n",
        "log_to_syslog_level = info\n",
        "log_to_syslog = True\n",
        "osd_pool_default_size = 2\n",
        "osd_pool_default_min_size = 1\n",
        "log_file = /var/log/ceph/radosgw.log\n",
        "osd_pool_default_pg_num = 128\n",
        "public_network = 10.21.7.0/24\n",
        "log_to_syslog_facility = LOG_LOCAL0\n",
        "osd_journal_size = 2048\n",
        "auth_supported = cephx\n",
        "osd_pool_default_pgp_num = 128\n",
        "osd_mkfs_type = xfs\n",
        "cluster_network = 10.21.9.0/24\n",
        "osd_recovery_max_active = 1\n",
        "osd_max_backfills = 1\n",
        "\n",
        "\n",
        "[client]\n",
        "rbd cache writethrough until flush = True\n",
        "rbd cache = True\n",
        "rbd_cache_writethrough_until_flush = True\n",
        "rbd_cache = True",
    ]
)])
def test_change_fsid(mocker, node, fsid, edit_conf, expected_conf, conf_file):
    sftp_mock = mocker.patch("octane.util.ssh.sftp")
    new_mock = mock.Mock()
    update_file_mock = mocker.patch("octane.util.ssh.update_file")
    update_file_mock.return_value.__enter__.return_value = (
        edit_conf, new_mock)
    upgrade_ceph.change_fsid(conf_file, node, fsid)
    write_calls = [mock.call(l.format(fsid_value=fsid)) for l in expected_conf]
    assert write_calls == new_mock.write.call_args_list
    sftp_mock.assert_called_once_with(node)
    update_file_mock.assert_called_once_with(sftp_mock.return_value, conf_file)


@pytest.mark.parametrize("conf,expected", [
    (
        "\nmon_initial_members = node-1 node-2 node-3\n",
        ["node-1", "node-2", "node-3"]
    ),
    ("Bla bla", None)
])
def test_get_initial_members(conf, expected):
    assert expected == upgrade_ceph.get_initial_members(conf)


@pytest.mark.parametrize("conf,expected", [
    (
        "\nmon_host = 10.21.7.3 10.21.7.4 10.21.7.5\n",
        ["10.21.7.3", "10.21.7.4", "10.21.7.5"]
    ),
    ("Bla bla", None)
])
def test_get_hosts(conf, expected):
    assert expected == upgrade_ceph.get_hosts(conf)
