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


def test_get_one_node_of(mocker):
    get_nodes = mocker.patch('octane.util.env.get_nodes')
    get_nodes.return_value = iter(['node1', 'node2'])

    node = env_util.get_one_node_of(mock.Mock(), 'controller')
    assert node == 'node1'


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

ENV_SETTINGS = {
    'editable': {
        'public_ssl': {
            'horizon': {
                'value': None
            },
            'services': {
                'value': None
            }
        },
        'external_ntp': {
            'ntp_list': {
                'value': None
            }
        },
        'external_dns': {
            'dns_list': {
                'value': None
            }
        },
        'provision': {
            'method': {
                'value': None
            }
        }
    }
}


def test_copy_vips(mock_subprocess):
    env_id = -1
    env = mock.Mock(data={'id': env_id})
    env_util.copy_vips(env)

    mock_subprocess.assert_called_once_with(
        ['fuel2', '--debug', 'env', 'copy', 'vips', str(env_id)]
    )


@pytest.mark.parametrize("env_id,master_ip", [(1, '10.0.0.1')])
@pytest.mark.parametrize("format_tuples", [
    [
        # (path, release_template, expected_result)
        ('/boot', "{settings.MASTER_IP}_{cluster.id}", "10.0.0.1_1"),
        (
            '/',
            "{cluster.id}_{settings.MASTER_IP}_blabal.tar.gz",
            "1_10.0.0.1_blabal.tar.gz"
        ),
    ]
])
def test_change_env_settings(mocker, env_id, master_ip, format_tuples):
    env = mocker.patch("fuelclient.objects.environment.Environment")
    env_dict = {
        'provision': {
            'image_data': {f[0]: {'uri': 'bad_value'} for f in format_tuples}}
    }
    expected_dict = {
        'provision': {
            'image_data': {f[0]: {'uri': f[2]} for f in format_tuples}}
    }
    release_dict = {
        'generated': {
            'provision': {
                'image_data': {f[0]: {'uri': f[1]} for f in format_tuples}}
        }
    }
    sql_call_mock = mocker.patch(
        "octane.util.sql.run_psql",
        side_effect=[
            json.dumps(env_dict), json.dumps(release_dict), 1
        ]
    )
    mock_json_dumps = mocker.patch("json.dumps", return_value="generated_json")
    mock_env = env.return_value = mock.Mock()
    mock_env.data = {"release_id": 1}
    mock_env.get_attributes.return_value = ENV_SETTINGS
    env_util.change_env_settings(env_id, master_ip)
    mock_env.update_attributes.assert_called_once_with({
        'editable': {
            'public_ssl': {
                'horizon': {
                    'value': False
                },
                'services': {
                    'value': False
                }
            },
            'external_ntp': {
                'ntp_list': {
                    'value': master_ip
                }
            },
            'external_dns': {
                'dns_list': {
                    'value': master_ip
                }
            },
            'provision': {
                'method': {
                    'value': 'image'
                }
            }
        }
    })
    mock_json_dumps.assert_called_once_with(expected_dict)
    sql_call_mock.assert_called_with(
        "update attributes set generated='{0}' where cluster_id={1}".format(
            mock_json_dumps.return_value, env_id
        ),
        'nailgun'
    )


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


@pytest.mark.parametrize("provision,compat", [
    (True, True,),
    (False, True),
])
def test_move_nodes(mocker, mock_subprocess, provision, compat):
    env = mock.Mock()
    env.data = {
        'id': 'test-id',
    }
    nodes = [mock.Mock(), mock.Mock()]

    for idx, node in enumerate(nodes):
        node.data = {'id': str(idx)}

    mock_create_configdrive = mocker.patch(
        "octane.util.disk.create_configdrive_partition")
    mock_update_node_partinfo = mocker.patch(
        "octane.util.disk.update_node_partition_info")
    mock_wait_for = mocker.patch(
        "octane.util.env.wait_for_nodes")
    mock_get_provision_method = mocker.patch(
        "octane.util.env.incompatible_provision_method")
    mock_get_provision_method.return_value = compat
    env_util.move_nodes(env, nodes, provision)
    if provision:
        assert mock_create_configdrive.call_args_list == \
            [mock.call(node) for node in nodes]
        assert mock_update_node_partinfo.call_args_list == \
            [mock.call(node.data["id"]) for node in nodes]
        mock_wait_for.assert_called_once_with(nodes, 'provisioned')
    else:
        assert mock_create_configdrive.call_args_list == []
        assert mock_update_node_partinfo.call_args_list == []
        assert mock_wait_for.call_args_list == []
