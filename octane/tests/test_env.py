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


@pytest.mark.parametrize("mock_method,version,expected_result",
                         [("cobbler", "5.1.1", True),
                          ("image", "6.0", False),
                          ("cobbler", "6.0", True),
                          ("image", "6.0", False),
                          ("image", "7.0", False),
                          ("image", "", False),
                          (None, None, False)])
def test_incompatible_provision_method(mocker,
                                       mock_method,
                                       version,
                                       expected_result):
    mock_env = mock.Mock()
    mock_env.data = {"fuel_version": version, "id": "test"}
    mock_get_method = mocker.patch("octane.util.env.get_env_provision_method")
    mock_get_method.return_value = mock_method
    if version:
        result = env_util.incompatible_provision_method(mock_env)
        assert expected_result == result
    else:
        with pytest.raises(Exception) as exc_info:
            env_util.incompatible_provision_method(mock_env)
        assert ("Cannot find version of environment {0}:"
                " attribute 'fuel_version' missing or has incorrect value"
                .format(mock_env.data["id"])) == exc_info.value.args[0]
