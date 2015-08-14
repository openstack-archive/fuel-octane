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

import logging
import time

from octane import magic_consts
from octane.util import ssh

from octane.commands.upgrade_db import get_controllers
from octane.helpers import transformations as ts

LOG = logging.getLogger(__name__)


def install_openvswitch(node):
    ssh.call(['apt-get',
              'install',
              '-y',
              'openvswitch-switch'],
              node=node)


def set_bridge_mtu(node, bridge):
    cmd = ['ip', 'link', 'set',
           'dev', bridge,
           'mtu', '1450']
    ssh.call(cmd, node=node)


def create_ovs_bridge(node, bridge):
    cmd = ['ovs-vsctl', 'add-br', bridge]
    ssh.call(cmd, node=node)


def create_lnx_bridge(node, bridge):
    cmd = ['brctl', 'addbr', bridge]
    ssh.call(cmd, node=node)


def create_tunnel_from_node_ovs(local, remote, bridge, key):
    gre_port = '%s--gre-%s' % (bridge, remote.data['ip'])
    cmd = ['ovs-vsctl', 'add-port', gre_port,
           '--', 'set', 'Interface', gre_port,
           'type=gre',
           'options:remote_ip=%s' % (remote.data['ip'],),
           'options:key=%d' % (key,)]
    ssh.call(cmd, node=local)


def create_tunnel_from_node_lnx(local, remote, bridge, key):
    gre_port = '%s--gre-%s' % (bridge, remote.data['ip'])
    cmd = ['ip', 'tunnel', 'add', gre_port,
           'mode', 'gre',
           'remote', remote.data['ip'],
           'local', local.data['ip'],
           'ttl', '255']
    ssh.call(cmd, node=local)
    cmd = ['brctl', 'addif', gre_port, bridge]
    ssh.call(cmd, node=local)


create_tunnel_providers = {
    'lnx': create_tunnel_from_node_lnx,
    'ovs': create_tunnel_from_node_ovs
}
create_bridge_providers = {
    'lnx': create_lnx_bridge,
    'ovs': create_ovs_bridge
}


def create_overlay_networks(node, hub, env, provider):
    create_tunnel_from_node = create_tunnel_providers[provider]
    key = node.data['id']
    for bridge in magic_consts.BRIDGES:
        create_tunnel_from_node(node, hub, bridge, key)
        create_tunnel_from_node(hub, node, bridge, key)


def isolate(node, env, deployment_info):
    nodes = list(get_controllers(env))
    if node.id not in [n.id for n in nodes]:
        LOG.info("Node is not a controller: %s", node)
        return
    for info in deployment_info:
        actions = ts.get_actions(info)
        LOG.info("Network scheme actions for node %s: %s",
                 node.id, actions)
    for bridge in magic_consts.BRIDGES:
        provider = ts.get_bridge_provider(actions, bridge)
        LOG.info("Found provider for bridge %s: %s", bridge, provider)
        if provider == 'ovs' and bridge == magic_consts.BRIDGES[0]:
            LOG.info("Installing openvswitch to node %s", node.id)
            install_openvswitch(node)
        create_bridge = create_bridge_providers[provider]
        create_bridge(node, bridge)
        if len(nodes) > 1:
            hub = nodes[-1] if nodes[0] == node else nodes[0]
            LOG.info("Creating tun for bridge %s on node %s, hub %s",
                     bridge, node.id, hub.id)
            create_overlay_networks(node, hub, env, provider)


def list_tunnels(node, bridge):
    tunnels, _ = ssh.call(['ovs-vsctl', 'list-ports', bridge],
                          stdout=ssh.PIPE,
                          node=node)
    return tunnels


def delete_tunnels_from_node(node, bridge):
    tunnels = list_tunnels(node, bridge)
    for tun in tunnels:
        ssh.call(['ovs-vsctl', 'del-port', bridge, tun],
                 node=node)


def delete_overlay_network(env, bridge):
    nodes = list(get_controllers(env))
    for node in nodes:
        delete_tunnels_from_node(node, bridge)


def delete_port_ovs(bridge, port):
    bridges = port['bridges']
    port_name = "%s--%s" % (bridges[0], bridge[1])
    return ['ovs-vsctl', 'del-port', bridge, port_name]


def delete_port_lnx(bridge, port):
    return ['brctl', 'delif', bridge, port['name']]


delete_port_providers = {
    'ovs': delete_port_ovs,
    'lnx': delete_port_lnx
}


def delete_patch_ports(node, host_config):
    for bridge in magic_consts.BRIDGES:
        port = ts.get_patch_port_action(host_config, bridge)
        provider = port.get('provider', 'lnx')
        delete_port_cmd = delete_port_providers[provider]
        cmd = delete_port_cmd(bridge, port)
        ssh.call(cmd, node=node)


def create_port_ovs(bridge, port):
    cmds = []
    tags = port.get('tags', ['', ''])
    trunks = port.get('trunks', [])
    bridges = port.get('bridges', [])
    for tag in tags:
        tag = "tag=%s" % (str(tag),) if tag else ''
    trunk = ''
    trunk_str = ','.join(trunks)
    if trunk_str:
        trunk = 'trunks=[%s]' % (trunk_str,)
    if bridges:
        br_patch = "%s--%s" % (bridges[0], bridges[1])
        ph_patch = "%s--%s" % (bridges[1], bridges[0])
        cmds.append(['ovs-vsctl', 'add-port',
                    bridge, br_patch,
                    tag[0], trunk,
                    '--', 'set',
                    'interface', br_patch,
                    'type=patch',
                    'options:peer=%s' % ph_patch])
        cmds.append(['ovs-vsctl', 'add-port',
                    bridge, ph_patch,
                    tag[1], trunk,
                    '--', 'set',
                    'interface', ph_patch,
                    'type=patch',
                    'options:peer=%s' % br_patch])
    return cmds


def create_port_lnx(bridge, port):
    port_name = port.get('name')
    if port_name:
        return [
            ['brctl', 'addif', bridge, port['name']],
            ['ip', 'link', 'set', 'up', 'dev', port['name']]
        ]
    else:
        raise Exception("No name for port: %s", port)


def create_patch_ports(node, host_config):
    for bridge in magic_consts.BRIDGES:
        port, provider = ts.get_patch_port(host_config, bridge)
        create_port_cmd = create_port_providers(provider)
        cmds = create_port_cmd(bridge, port)
        for cmd in cmds:
            ssh.call(cmd, node=node)
