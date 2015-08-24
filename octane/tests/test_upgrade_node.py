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

from octane.commands import upgrade_node


def test_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.upgrade_node.upgrade_node')
    octane_app.run(["upgrade-node", "--isolated", "1", "2", "3"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, [2, 3], isolated=True)


def test_parse_tenant_get():
    res = upgrade_node.parse_tenant_get(TENANT_GET_SAMPLE, 'id')
    assert res == 'e26c8079d61f46c48f9a6d606631ee5e'

TENANT_GET_SAMPLE = """
+-------------+-----------------------------------+
|   Property  |               Value               |
+-------------+-----------------------------------+
| description | Tenant for the openstack services |
|   enabled   |                True               |
|      id     |  e26c8079d61f46c48f9a6d606631ee5e |
|     name    |              services             |
+-------------+-----------------------------------+
"""[1:]
