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

from octane import magic_consts
from octane.util import env as env_util


@pytest.fixture
def mock_os_path(mocker):
    res = mocker.patch('os.path')
    res.exists.return_value = True
    res.dirname.return_value = magic_consts.FUEL_CACHE
    return res


def test_find_node_deployment_info():
    roles = ['controller', 'primary-controller']
    node = mock.Mock()
    node.id = 1
    res = env_util.find_node_deployment_info(node, roles, DEPLOYMENT_INFO)
    assert res == DEPLOYMENT_INFO[0]


def test_find_node_deployment_info_none():
    roles = ['controller', 'primary-controller']
    node = mock.Mock()
    node.id = 2
    res = env_util.find_node_deployment_info(node, roles, DEPLOYMENT_INFO)
    assert res is None


DEPLOYMENT_INFO = [{
    'uid': '1',
    'role': 'primary-controller',
    'nodes': [{
        'uid': '1',
        'role': 'primary-controller',
        'name': 'test',
    }, {
        'uid': '1',
        'role': 'zabbix',
        'name': 'test',
    }, {
        'uid': '2',
        'role': 'compute',
        'name': 'test2',
    }],
}, {
    'uid': '1',
    'role': 'zabbix',
    'nodes': [{
        'uid': '1',
        'role': 'primary-controller',
        'name': 'test',
    }, {
        'uid': '1',
        'role': 'zabbix',
        'name': 'test',
    }, {
        'uid': '2',
        'role': 'compute',
        'name': 'test2',
    }],
}, {
    'uid': '2',
    'role': 'compute',
    'nodes': [{
        'uid': '1',
        'role': 'primary-controller',
        'name': 'test',
    }, {
        'uid': '1',
        'role': 'zabbix',
        'name': 'test',
    }, {
        'uid': '2',
        'role': 'compute',
        'name': 'test2',
    }],
}]


def test_parse_tenant_get():
    res = env_util.parse_tenant_get(TENANT_GET_SAMPLE, 'id')
    assert res == 'e26c8079d61f46c48f9a6d606631ee5e'


def test_cache_service_tenant_id(mocker, mock_open, mock_os_path, node):
    mock_open.return_value.readline.return_value = '111'
    test_env = mock.Mock()
    test_env.data = {
        'id': 111,
    }
    res = env_util.cache_service_tenant_id(test_env, node)
    assert res == '111'

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


def test_copy_vips(mock_subprocess):
    env_id = -1
    env = mock.Mock(data={'id': env_id})
    env_util.copy_vips(env)

    mock_subprocess.assert_called_once_with(
        ['fuel2', 'env', 'copy', 'vips', str(env_id)]
    )


@pytest.mark.parametrize("data, exception", [
    (
        '[{"ID": "2aed71d8816f4e5f8d4ad06836521d49", "Name": "admin"}, '
        '{"ID": "09f1c11740ba4bc399387f3995d5160e", "Name": "services"}]',
        False
    ),
    (
        '[{"id": "2aed71d8816f4e5f8d4ad06836521d49", "name": "admin"}, '
        '{"id": "09f1c11740ba4bc399387f3995d5160e", "name": "services"}]',
        False,
    ),
    (
        '[{"ID": "2aed71d8816f4e5f8d4ad06836521d49", "NAME": "admin"}, '
        '{"ID": "09f1c11740ba4bc399387f3995d5160e", "NAME": "services"}]',
        False
    ),
    (
        '[{"ID": "2aed71d8816f4e5f8d4ad06836521d49", "NAME": "admin"}]',
        True
    ),
])
@pytest.mark.parametrize("key,value", [
    ("services", "09f1c11740ba4bc399387f3995d5160e"),
    ("Services", "09f1c11740ba4bc399387f3995d5160e"),
    ("SERVICES", "09f1c11740ba4bc399387f3995d5160e"),
])
def test_openstack_project_value(mocker, data, key, value, exception):
    env = mock.Mock()
    node = mock.Mock()
    mocker.patch("octane.util.env.get_admin_password", return_value="pswd")
    mocker.patch("octane.util.ssh.call_output", return_value=data)
    if exception:
        with pytest.raises(Exception) as exc_info:
            env_util.get_openstack_project_value(env, node, key)
        assert "Field {0} not found in openstack project list".format(key) == \
            exc_info.value.message
    else:
        assert value == env_util.get_openstack_project_value(env, node, key)


@pytest.mark.parametrize("node", [mock.Mock(), None])
def test_get_service_tenant_id(mocker, node):
    mock_obj = mocker.patch("octane.util.env.get_openstack_project_value")
    env = mock.Mock()
    env_util.get_service_tenant_id(env, node)
    mock_obj.assert_called_once_with(env, node, "services")
