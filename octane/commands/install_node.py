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

from octane.commands.upgrade_db import get_controllers
from octane.commands.upgrade_node import ControllerUpgrade
from octane.commands.upgrade_node import wait_for_node
from octane.helpers.node_attributes import copy_disks
from octane.helpers.node_attributes import copy_ifaces

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj

LOG = logging.getLogger(__name__)


def update_node_settings(node, disks_fixture, ifaces_fixture):
    disks = node.get_attribute('disks')
    new_disks = copy_disks(disks_fixture, disks, 'by_extra')
    node.upload_node_attributes('disks', new_disks)

    ifaces = node.get_attribute('interfaces')
    new_ifaces = copy_ifaces(ifaces_fixture, ifaces)
    node.upload_node_attributes('interfaces', new_ifaces)


def install_node(orig_id, seed_id, node_ids, isolated=False):
    env = environment_obj.Environment
    nodes = [node_obj.Node(node_id) for node_id in node_ids]
    if orig_id == seed_id:
        raise Exception("Original and seed environments have the same ID: %s",
                        orig_id)
    orig_env = env(orig_id)
    orig_node = next(get_controllers(orig_env))
    seed_env = env(seed_id)
    seed_env.assign(nodes, orig_node.data['roles'])
    for node in nodes:
        disk_info_fixture = orig_node.get_attribute('disks')
        nic_info_fixture = orig_node.get_attribute('interfaces')
        update_node_settings(node, disk_info_fixture, nic_info_fixture)

    seed_env.install_selected_nodes('provision', nodes)
    for node in nodes:
        wait_for_node(node, "provisioned")

    for node in nodes:
        ControllerUpgrade.predeploy(node, seed_env,
                                    isolated=isolated)
    seed_env.install_selected_nodes('deploy', nodes)
    for node in nodes:
        wait_for_node(node, "ready")


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
        return parser

    def take_action(self, parsed_args):
        install_node(parsed_args.orig_id, parsed_args.seed_id,
                     parsed_args.node_ids, isolated=parsed_args.isolated)
