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

from octane.handlers.upgrade import controller as controller_upgrade
from octane.helpers.node_attributes import copy_disks
from octane.helpers.node_attributes import copy_ifaces
from octane import magic_consts
from octane.util import env as env_util
from octane.util import network
from octane.util import node as node_util

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


def isolate(nodes, env):
    nodes.sort(key=lambda node: node.id, reverse=True)
    hub = nodes[0]
    deployment_info = env_util.get_node_default_facts(
        env, nodes=[hub.data['id']])
    network.create_bridges(hub, env, deployment_info)
    for node in nodes[1:]:
        deployment_info = env_util.get_node_default_facts(
            env, nodes=[node.data['id']])
        network.setup_isolation(hub, node, env, deployment_info)
    for node in nodes:
        network.flush_arp(node)


def update_node_settings(node, disks_fixture, ifaces_fixture):
    if not magic_consts.DEFAULT_DISKS:
        LOG.info("Updating node %s disk settings with fixture: %s",
                 str(node.id), disks_fixture)
        disks = node.get_attribute('disks')
        LOG.info("Original node %s disk settings: %s",
                 str(node.id), disks)
        new_disks = list(copy_disks(disks_fixture, disks, 'by_name'))
        LOG.info("New disk info generated: %s", new_disks)
        node.upload_node_attribute('disks', new_disks)
    else:
        LOG.warn("Using default volumes for node %s", node)
        LOG.warn("To keep custom volumes layout, change DEFAULT_DISKS const "
                 "in magic_consts.py module")

    if not magic_consts.DEFAULT_NETS:
        LOG.info("Updating node %s network settings with fixture: %s",
                 str(node.id), ifaces_fixture)
        ifaces = node.get_attribute('interfaces')
        LOG.info("Original node %s network settings: %s",
                 str(node.id), ifaces)
        new_ifaces = list(copy_ifaces(ifaces_fixture, ifaces))
        LOG.info("New interfaces info generated: %s", new_ifaces)
        node.upload_node_attribute('interfaces', new_ifaces)
    else:
        LOG.warn("Using default networks for node %s", node)


class NoSuchNetwork(Exception):
    message = "Environment ID {0} doesn't have {1} network"

    def __init__(self, env_id, network):
        super(NoSuchNetwork, self).__init__(self.message.format(
            env_id, network))


def check_networks(orig_env, seed_env, networks):
    orig_networks = \
        [net['name'] for net in env_util.get_env_networks(orig_env)]
    seed_networks = \
        [net['name'] for net in env_util.get_env_networks(seed_env)]
    for net in networks:
        if net not in orig_networks:
            raise NoSuchNetwork(orig_env.data['id'], net)
        if net not in seed_networks:
            raise NoSuchNetwork(seed_env.data['id'], net)


def install_node(orig_id, seed_id, node_ids, isolated=False, networks=None):
    if orig_id == seed_id:
        raise Exception("Original and seed environments have the same ID: %s",
                        orig_id)

    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)
    check_networks(orig_env, seed_env, networks)

    nodes = [node_obj.Node(node_id) for node_id in node_ids]
    orig_node = env_util.get_one_controller(orig_env)
    seed_env.assign(nodes, orig_node.data['roles'])
    for node in nodes:
        disk_info_fixture = orig_node.get_attribute('disks')
        nic_info_fixture = orig_node.get_attribute('interfaces')
        update_node_settings(node, disk_info_fixture, nic_info_fixture)

    if networks:
        env_util.clone_ips(orig_id, networks)

    LOG.info("Nodes reboot in progress. Please wait...")
    node_util.reboot_nodes(nodes, timeout=180 * 60)
    node_util.wait_for_mcollective_start(nodes)
    env_util.provision_nodes(seed_env, nodes)

    env_util.update_deployment_info(seed_env, isolated)

    if isolated and len(nodes) > 1:
        isolate(nodes, seed_env)

    env_util.deploy_changes(seed_env, nodes)

    for node in nodes:
        controller_upgrade.ControllerUpgrade(
            node, seed_env, isolated=isolated).postdeploy()


class InstallNodeCommand(cmd.Command):
    """Install nodes to environment based on settings of orig environment"""

    def get_parser(self, prog_name):
        parser = super(InstallNodeCommand, self).get_parser(prog_name)
        parser.add_argument(
            '--isolated', action='store_true',
            help="Isolate node's network from original cluster")
        parser.add_argument(
            'orig_id', type=int, metavar='ORIG_ID',
            help="ID of original environment")
        parser.add_argument(
            'seed_id', type=int, metavar='SEED_ID',
            help="ID of upgrade seed environment")
        parser.add_argument(
            'node_ids', type=int, metavar='NODE_ID', nargs='+',
            help="IDs of nodes to be moved")
        parser.add_argument(
            '--networks', type=str, nargs='+', default=[],
            help="Names of networks which IPs should be copied")
        return parser

    def take_action(self, parsed_args):
        install_node(parsed_args.orig_id, parsed_args.seed_id,
                     parsed_args.node_ids, isolated=parsed_args.isolated,
                     networks=parsed_args.networks)
