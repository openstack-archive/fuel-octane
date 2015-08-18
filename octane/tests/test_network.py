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
from mock import call
from octane.helpers import network


def test_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.upgrade_node.upgrade_node')
    octane_app.run(["upgrade-node", "--isolated", "1", "2", "3"])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, [2, 3], isolated=True)


def test_isolate(mocker):
    node = mocker.MagicMock()
    node.id = 1
    node.data = {
        'id': node.id,
        'cluster': 101,
        'roles': ['controller']
    }
    node1 = mocker.MagicMock()
    node1.id = 2
    node1.data = {
        'id': node1.id,
        'cluster': 101,
        'roles': ['controller']
    }
    node2 = mocker.MagicMock()
    node2.id = 3
    node2.data = {
        'id': node2.id,
        'cluster': 101,
        'roles': [],
        'pending_roles': ['controller'],
    }
    env = mocker.MagicMock()
    env.data = {
        'id': 101,
    }
    deployment_info = {}
    mock_nodeobj = mocker.patch('fuelclient.objects.node.Node.get_all')
    mock_nodeobj.return_value = [node2, node, node1]
    mock_bridges = mocker.patch('octane.helpers.network.create_bridges')
    mock_networks = mocker.patch(
        'octane.helpers.network.create_overlay_networks')

    expected_args = [
        call(node, node1, env, deployment_info, 2),
        call(node, node2, env, deployment_info, 3),
    ]

    network.isolate(node, env, deployment_info)

    mock_bridges.assert_called_once_with(node, env, deployment_info)
    assert mock_networks.call_args_list == expected_args


def test_create_overlay_network(mocker):
    node1 = mocker.MagicMock()
    node1.id = 2
    node1.data = {
        'id': node1.id,
        'cluster': 101,
        'roles': ['controller'],
        'ip': '10.10.10.1',
    }
    node2 = mocker.MagicMock()
    node2.id = 3
    node2.data = {
        'id': node2.id,
        'cluster': 101,
        'roles': [],
        'pending_roles': ['controller'],
        'ip': '10.10.10.2',
    }
    env = mocker.MagicMock()
    env.data = {
        'id': 101,
    }
    deployment_info = [{
        'network_scheme': {
            'transformations': [{
                'action': 'add-br',
                'name': 'br-ex',
                'provider': 'ovs',
            }, {
                'action': 'add-br',
                'name': 'br-mgmt',
            }]
        }
    }]

    mock_ssh = mocker.patch('octane.util.ssh.call')

    expected_args = [
        call(['ovs-vsctl', 'add-port', 'br-ex', 'br-ex--gre-10.10.10.2',
              '--', 'set', 'Interface', 'br-ex--gre-10.10.10.2',
              'type=gre',
              'options:remote_ip=10.10.10.2',
              'options:key=2'],
             node=node1),
        call(['ip', 'link', 'add', 'gre3-3',
              'type', 'gretap',
              'remote', '10.10.10.2',
              'local', '10.10.10.1',
              'key', '3'],
             node=node1),
        call(['ip', 'link', 'set', 'up', 'dev', 'gre3-3'],
             node=node1),
        call(['ip', 'link', 'set', 'mtu', '1450', 'dev', 'gre3-3', ],
             node=node1),
        call(['brctl', 'addif', 'br-mgmt', 'gre3-3'],
             node=node1),
    ]

    network.create_overlay_networks(node1, node2, env, deployment_info,
                                    node1.id)

    assert mock_ssh.call_args_list == expected_args
