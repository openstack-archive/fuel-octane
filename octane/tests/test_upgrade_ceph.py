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
        handlers.append(ceph_osd.CephOsdUpgrade(node, env, False))
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
