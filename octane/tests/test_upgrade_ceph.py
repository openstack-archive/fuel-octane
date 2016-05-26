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

from octane.commands import upgrade_ceph


def test_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.upgrade_ceph.upgrade_ceph')
    octane_app.run(["upgrade-ceph", "1", "2"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, 2)

CEPH_CONF_BASE = "key = value\n"
CEPH_CONF_KEYRING = CEPH_CONF_BASE + \
    "[client.radosgw.gateway]\n"
CEPH_CONF_RGWFRONT = CEPH_CONF_KEYRING + \
    "rgw_frontends = fastcgi socket_port=9000 socket_host=127.0.0.1\n"


@pytest.mark.parametrize("conf,expected_res", [
    (CEPH_CONF_BASE, CEPH_CONF_BASE),
    (CEPH_CONF_KEYRING, CEPH_CONF_RGWFRONT),
    (CEPH_CONF_RGWFRONT, CEPH_CONF_RGWFRONT),
])
def test_add_rgw_frontends(mocker, conf, expected_res):
    res = upgrade_ceph.add_rgw_frontends(conf)
    assert expected_res == res
