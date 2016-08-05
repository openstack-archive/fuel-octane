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


@pytest.mark.parametrize("facts", [[{'uid': 1}, {'uid': 2}]])
@pytest.mark.parametrize("env_id", [1])
@pytest.mark.parametrize("os_path_exist", [True, False])
def test_write_facts_to_dir(mocker, mock_open, mock_os_path,
                            os_path_exist, facts, env_id):
    mock_os_makedirs = mocker.patch("os.makedirs")
    mock_os_path.exists.return_value = os_path_exist
    buf = io.BytesIO()
    mock_open.return_value.write.side_effect = buf.write
    mock_yaml = mocker.patch("yaml.safe_dump")
    env_util.write_facts_to_dir(facts, env_id)

    join_calls = [mock.call('/tmp', "deployment_{0}.orig".format(env_id))]
    join_calls.extend(
        [mock.call(mock_os_path.join.return_value,
                   "{0}.yaml".format(fact['uid'])) for fact in facts])

    mock_os_path.join.assert_has_calls(join_calls)
    mock_open.assert_called_with(mock_os_path.join(), "w")

    mock_yaml.assert_has_calls(
        [mock.call(fact, mock_open.return_value, default_flow_style=False)
         for fact in facts]
    )
    if not os_path_exist:
        mock_os_makedirs.assert_called_once_with(
            mock_os_path.join.return_value
        )
    else:
        mock_os_makedirs.assert_not_called()


@pytest.mark.parametrize("env_id", [1])
def test_get_dir_deployment_info(mock_os_path, env_id):
    env_util.get_dir_deployment_info(env_id)
    mock_os_path.join.assert_called_once_with(
        '/tmp', "deployment_{0}.orig".format(env_id)
    )


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

NORMALIZED_DATA = [
    {"name": "test", "id": 2},
    {"name": "test"},
]


@pytest.mark.parametrize("normalized_data,is_error",
                         zip(NORMALIZED_DATA, [False, True]))
def test_clone_env(mocker, normalized_data, is_error):
    release = mock.Mock(data={'name': "14.04", 'id': 2})
    mock_fuel_call = mocker.patch('octane.util.env.fuel2_env_call')
    mock_json_loads = mocker.patch('json.loads')
    mock_normalized = mocker.patch(
        'octane.util.helpers.normalized_cliff_show_json'
    )
    mock_normalized.return_value = normalized_data
    orig_id = 1
    if not is_error:
        seed_id = env_util.clone_env(orig_id, release)
        assert seed_id == 2
        mock_json_loads.assert_called_once_with(mock_fuel_call.return_value)
    else:
        with pytest.raises(Exception) as exc_info:
            assert ("Couldn't find new environment ID in fuel CLI output:"
                    "\n{0}".format(normalized_data)) == exc_info.value.args[0]


def test_copy_vips(mock_subprocess):
    env_id = -1
    env = mock.Mock(data={'id': env_id})
    env_util.copy_vips(env)

    mock_subprocess.assert_called_once_with(
        ['fuel2', '--debug', 'env', 'copy', 'vips', str(env_id)]
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
