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

from octane.commands import upgrade_node


@pytest.mark.parametrize('live_migration', [True, False])
def test_parser(mocker, octane_app, live_migration):
    m = mocker.patch('octane.commands.upgrade_node.upgrade_node')
    cmd = ["upgrade-node", "--isolated", "1", "2", "3"]
    if not live_migration:
        cmd = cmd + ["--no-live-migration"]
    octane_app.run(cmd)
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(
        1, [2, 3],
        isolated=True, live_migration=live_migration)


@pytest.mark.parametrize(
    "node_ids,isolated,provision,roles",
    [(['test-node-1', 'test-node-2', 'test-node-3'],
      False, True, None), ])
def test_upgrade_node(mocker, node_ids, isolated, provision, roles):
    nodes = []

    def _create_node(node_id):
        node = mock.Mock('node', spec_set=['data', 'id'])
        node.id = node_id
        node.data = {}
        node.data['id'] = node_id
        node.data['cluster'] = None
        node.data['roles'] = 'controller'
        nodes.append(node)
        return node

    test_env_id = 'test-env'
    mock_env = mocker.patch("fuelclient.objects.environment.Environment")
    mock_env.id = test_env_id
    mock_env.data = {}
    mock_env.data['id'] = mock_env.id
    mocker.patch("octane.util.patch.applied_patch")
    mock_node = mocker.patch("fuelclient.objects.node.Node")
    mock_node.side_effect = _create_node
    mock_copy_patches = mocker.patch(
        "octane.commands.upgrade_node.copy_patches_folder_to_nailgun")
    mock_get_handlers = mocker.patch(
        "octane.handlers.upgrade.get_nodes_handlers")
    mock_handlers = mock_get_handlers.return_value
    mock_move_nodes = mocker.patch("octane.util.env.move_nodes")
    mock_deploy_nodes = mocker.patch("octane.util.env.deploy_nodes")
    mock_deploy_changes = mocker.patch("octane.util.env.deploy_changes")
    upgrade_node.upgrade_node(test_env_id, node_ids)
    mock_copy_patches.assert_called_once_with()
    mock_move_nodes.assert_called_once_with(mock_env.return_value, nodes)
    assert mock_handlers.call_args_list == [
        mock.call('preupgrade'), mock.call('prepare'),
        mock.call('predeploy'), mock.call('postdeploy')]
    if isolated:
        mock_deploy_nodes.assert_called_once_with(mock_env.return_value, nodes)
    else:
        mock_deploy_changes.assert_called_once_with(
            mock_env.return_value, nodes)


@pytest.mark.parametrize('node_data,expected_error', [
    ([{
        'id': 'test-node',
        'cluster': None,
    }], None),
    ([{
        'id': 'test-node',
        'cluster': 'test-env',
    }], Exception),
    ([{
        'id': 'test-node',
        'cluster': 'test-env-1',
    }, {
        'id': 'another-test-node',
        'cluster': 'test-env-2'
    }], Exception),
])
def test_check_sanity(mocker, node, node_data, expected_error):
    test_env_id = "test-env"
    mock_nodes = []
    for data in node_data:
        mock_node = mocker.Mock(data=data)
        mock_nodes.append(mock_node)
    if expected_error:
        with pytest.raises(expected_error) as exc_info:
            upgrade_node.check_sanity(test_env_id, mock_nodes)
        if len(mock_nodes) == 1:
            assert "Cannot upgrade node with ID %s:" \
                in exc_info.value.args[0]
        else:
            assert "Not upgrading nodes from different clusters" \
                in exc_info.value.args[0]
    else:
        assert upgrade_node.check_sanity(test_env_id, mock_nodes) is None
