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
import yaml

from octane.commands import upgrade_node


@pytest.mark.parametrize('cmd,env,nodes,provision,roles', [
    (["upgrade-node", "--isolated", "1", "2", "3"], 1, [2, 3], True, None),
    (["upgrade-node", "--isolated", "--no-provision", "4", "5"], 4, [5], False,
     None),
    (["upgrade-node", "--isolated", "--roles=role-a,role-b", "6", "7"], 6, [7],
     True, ["role-a", "role-b"]),
    (["upgrade-node", "--isolated", "--no-provision", "--roles=role-c,role-d",
      "8", "9"], 8, [9], False, ["role-c", "role-d"]),
])
def test_parser(mocker, octane_app, cmd, env, nodes, provision, roles):
    m = mocker.patch('octane.commands.upgrade_node.upgrade_node')
    octane_app.run(cmd)
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(env, nodes, isolated=True, network_template=None,
                              provision=provision, roles=roles)


def test_check_sanity(mocker, node):
    test_cluster_id = 'test-env'
    mock_env_data = {
        'id': test_cluster_id,
    }
    mock_node_data = {
        'id': 'test-node',
        'cluster': None,
    }
    mock_env = mocker.Mock()
    mock_node = mocker.Mock()
    mock_env.data = mock_env_data
    mock_node.data = mock_node_data
    mock_nodes = [mock_node, ]
    res = upgrade_node.check_sanity(mock_env, mock_nodes)
    assert res


@pytest.mark.parametrize("return_value", [{'test': 'test'}, ])
@pytest.mark.parametrize("side_effect",
                         [None, yaml.parser.ParserError, IOError])
def test_load_network_template(mocker, return_value, side_effect):
    mocker.patch("octane.util.helpers.load_yaml",
                 return_value=return_value,
                 side_effect=side_effect)
    if side_effect:
        with pytest.raises(side_effect):
            upgrade_node.load_network_template("testfile")
    else:
        assert return_value == upgrade_node.load_network_template("testfile")
