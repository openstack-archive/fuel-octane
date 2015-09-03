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
import re
import subprocess

from octane import magic_consts
from octane.util import ssh

from octane.helpers import transformations as ts

LOG = logging.getLogger(__name__)


def install_openvswitch(node, master_ip):
    cmds = []
    cmds.append(
        ['sh', '-c',
         'echo'
         ' "deb http://{0}:8080/2015.1.0-7.0/ubuntu/x86_64 mos7.0'
         ' main restricted" >> /etc/apt/sources.list'.format(master_ip)])
    cmds.append(['apt-get', 'update'])
    cmds.append(
        ['apt-get', 'install', '-y', '--force-yes', 'openvswitch-switch'])
    cmds.append(['sh', '-c', 'sed -i 1,2d /etc/apt/sources.list'])
    for cmd in cmds:
        ssh.call(cmd, node=node)


def set_bridge_mtu(node, bridge):
    ssh.call(['ip', 'link', 'set', 'dev', bridge, 'mtu', '1450'], node=node)


def create_ovs_bridge(node, bridge):
    cmds = []
    cmds.append(['ovs-vsctl', 'add-br', bridge])
    cmds.append(['ip', 'link', 'set', 'up', 'dev', bridge])
    cmds.append(['ip', 'link', 'set', 'mtu', '1450', 'dev', bridge])
    for cmd in cmds:
        ssh.call(cmd, node=node)


def create_lnx_bridge(node, bridge):
    cmd = ['brctl', 'addbr', bridge]
    ssh.call(cmd, node=node)


def create_tunnel_from_node_ovs(local, remote, bridge, key, admin_iface):
    def check_tunnel(node, bridge, port):
        cmd = ['sh', '-c',
               'ovs-vsctl list-ports %s | grep -q %s' % (bridge, port)]
        try:
            ssh.call(cmd, node=node)
        except subprocess.CalledProcessError:
            return False
        else:
            return True

    gre_port = '%s--gre-%s' % (bridge, remote.data['ip'])
    if check_tunnel(local, bridge, gre_port):
        return
    cmd = ['ovs-vsctl', 'add-port', bridge, gre_port,
           '--', 'set', 'Interface', gre_port,
           'type=gre',
           'options:remote_ip=%s' % (remote.data['ip'],),
           'options:key=%d' % (key,)]
    ssh.call(cmd, node=local)


def create_tunnel_from_node_lnx(local, remote, bridge, key, admin_iface):
    def check_tunnel(node, port):
        cmd = ['sh', '-c',
               'ip link show dev %s' % (port,)]
        try:
            ssh.call(cmd, node=node)
        except subprocess.CalledProcessError:
            return False
        else:
            return True

    gre_port = 'gre%s-%s' % (remote.id, key)

    if check_tunnel(local, gre_port):
        return
    cmds = []
    cmds.append(['ip', 'link', 'add', gre_port,
                 'type', 'gretap',
                 'remote', remote.data['ip'],
                 'local', local.data['ip'],
                 'key', str(key)])
    cmds.append(['ip', 'link', 'set', 'up', 'dev', gre_port])
    cmds.append(['ip', 'link', 'set', 'mtu', '1450', 'dev', gre_port])
    cmds.append(['ip', 'link', 'set', 'up', 'dev', bridge])
    cmds.append(['brctl', 'addif', bridge, gre_port])
    for cmd in cmds:
        ssh.call(cmd, node=local)


create_tunnel_providers = {
    'lnx': create_tunnel_from_node_lnx,
    'ovs': create_tunnel_from_node_ovs
}
create_bridge_providers = {
    'lnx': create_lnx_bridge,
    'ovs': create_ovs_bridge
}


def create_bridges(node, env, deployment_info):
    for info in deployment_info:
        actions = ts.get_actions(info)
        LOG.info("Network scheme actions for node %s: %s",
                 node.id, actions)
        master_ip = info["master_ip"]
    for bridge in magic_consts.BRIDGES:
        provider = ts.get_bridge_provider(actions, bridge)
        LOG.info("Found provider for bridge %s: %s", bridge, provider)
        if provider == 'ovs' and bridge == magic_consts.BRIDGES[0]:
            LOG.info("Installing openvswitch to node %s", node.id)
            install_openvswitch(node, master_ip)
        create_bridge = create_bridge_providers[provider]
        create_bridge(node, bridge)


def create_overlay_networks(node, remote, env, deployment_info, key=0):
    """Create GRE tunnels between a node and other nodes in the environment

    Building tunnels for all bridges listed in constant BRIDGES.

    :param: node
    :param: remote
    :param: env
    :param: deployment_info
    :param: key
    """

    for info in deployment_info:
        actions = ts.get_actions(info)
    for bridge in magic_consts.BRIDGES:
        provider = ts.get_bridge_provider(actions, bridge)
        admin_iface = ts.get_admin_iface(actions)
        create_tunnel_from_node = create_tunnel_providers[provider]
        LOG.info("Creating tun for bridge %s on node %s, remote %s",
                 bridge, node.id, remote.id)
        create_tunnel_from_node(node, remote, bridge, key,
                                admin_iface)
        key += 1


def setup_isolation(hub, node, env, deployment_info):
    """Create bridges and overlay networks for the given node

    Isolate a given node in the environment from networks connected to
    bridges from maigc_consts.BRIDGES list. Create bridges on the node and
    create tunnels that constitute overlay network on top of the admin network.
    It ensures that nodes are connected during the deployment, as required.

    If there's only 1 controller node in the environment, there's no need to
    create any tunnels.

    :param: node
    :param: env
    :param: deployment_info
    """

    create_bridges(node, env, deployment_info)
    create_overlay_networks(hub,
                            node,
                            env,
                            deployment_info,
                            node.id)
    create_overlay_networks(node,
                            hub,
                            env,
                            deployment_info,
                            node.id)


def list_tunnels_ovs(node, bridge):
    tunnels = []
    stdout, _ = ssh.call(['ovs-vsctl', 'list-ports', bridge],
                         stdout=ssh.PIPE,
                         node=node)
    for match in re.finditer("[\S]+\n", stdout):
        tun = match.group(0)
        tunnels.append(tun[:-1])
    return tunnels


def delete_tunnels_ovs(node, bridge):
    tunnels = list_tunnels_ovs(node, bridge)
    for tun in tunnels:
        ssh.call(['ovs-vsctl', 'del-port', bridge, tun],
                 node=node)


def list_tunnels_lnx(node, bridge):
    tunnels = []
    gre_port_re = "gre[0-9]+-[0-9]+".format(node.id)
    stdout, _ = ssh.call(['brctl', 'show', bridge],
                         stdout=ssh.PIPE,
                         node=node)
    for match in re.finditer(gre_port_re, stdout):
        tunnels.append(match.group(0))
    return tunnels


def delete_tunnels_lnx(node, bridge):
    tunnels = list_tunnels_lnx(node, bridge)
    for tun in tunnels:
        ssh.call(['brctl', 'delif', bridge, tun], node=node)
        ssh.call(['ip', 'link', 'delete', tun], node=node)


delete_tunnels = {
    'lnx': delete_tunnels_lnx,
    'ovs': delete_tunnels_ovs
}


def delete_overlay_networks(node, host_config):
    for bridge in magic_consts.BRIDGES:
        actions = ts.get_actions(host_config)
        provider = ts.get_bridge_provider(actions, bridge)
        delete_tunnels_cmd = delete_tunnels[provider]
        delete_tunnels_cmd(node, bridge)


def delete_port_ovs(bridge, port):
    bridges = port['bridges']
    port_name = "%s--%s" % (bridges[0], bridges[1])
    return ['ovs-vsctl', 'del-port', bridges[0], port_name]


def delete_port_lnx(bridge, port):
    return ['brctl', 'delif', bridge, port['name']]


delete_port_providers = {
    'ovs': delete_port_ovs,
    'lnx': delete_port_lnx
}


def delete_patch_ports(node, host_config):
    for bridge in magic_consts.BRIDGES:
        port, provider = ts.get_patch_port_action(host_config, bridge)
        delete_port_cmd = delete_port_providers[provider]
        cmd = delete_port_cmd(bridge, port)
        ssh.call(cmd, node=node)


def create_port_ovs(bridge, port):
    cmds = []
    tags = port.get('tags', ['', ''])
    trunks = port.get('trunks', [])
    bridges = port.get('bridges', [])
    bridges.remove(bridge)
    ph_bridge = bridges[0]
    for tag in tags:
        tag = "tag=%s" % (str(tag),) if tag else ''
    trunk = ''
    trunk_str = ','.join(trunks)
    if trunk_str:
        trunk = 'trunks=[%s]' % (trunk_str,)
    if bridges:
        br_patch = "%s--%s" % (bridge, ph_bridge)
        ph_patch = "%s--%s" % (ph_bridge, bridge)
        cmds.append(['ovs-vsctl', 'add-port', bridge, br_patch, tags[0],
                     trunk, '--', 'set', 'interface', br_patch, 'type=patch',
                     'options:peer=%s' % ph_patch])
        cmds.append(['ovs-vsctl', 'add-port', ph_bridge, ph_patch, tags[1],
                     trunk, '--', 'set', 'interface', ph_patch, 'type=patch',
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


create_port_providers = {
    'lnx': create_port_lnx,
    'ovs': create_port_ovs
}


def create_patch_ports(node, host_config):
    for bridge in magic_consts.BRIDGES:
        port, provider = ts.get_patch_port_action(host_config, bridge)
        create_port_cmd = create_port_providers[provider]
        cmds = create_port_cmd(bridge, port)
        for cmd in cmds:
            ssh.call(cmd, node=node)


def flush_arp(node):
    cmd = ['ip', 'neigh', 'flush', 'all']
    ssh.call(cmd, node=node)
