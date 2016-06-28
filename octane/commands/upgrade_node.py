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
import os.path

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj

from octane.handlers import upgrade as upgrade_handlers
from octane import magic_consts
from octane.util import docker
from octane.util import env as env_util
from octane.util import patch

LOG = logging.getLogger(__name__)


def check_sanity(env_id, nodes):
    one_orig_id = None
    for node in nodes:
        node_id = node.data['id']
        orig_id = node.data['cluster']
        if orig_id == env_id:
            raise Exception(
                "Cannot upgrade node with ID %s: it's already in cluster with "
                "ID %s", node_id, env_id,
            )
        if orig_id:
            if one_orig_id and orig_id != one_orig_id:
                raise Exception(
                    "Not upgrading nodes from different clusters: %s and %s",
                    orig_id, one_orig_id,
                )
            one_orig_id = orig_id


def upgrade_node(env_id, node_ids, isolated=False, network_template=None,
                 provision=True, roles=None, live_migration=True):
    # From check_deployment_status
    env = environment_obj.Environment(env_id)
    nodes = [node_obj.Node(node_id) for node_id in node_ids]

    check_sanity(env_id, nodes)

    # NOTE(ogelbukh): patches and scripts copied to nailgun container
    # for later use
    copy_patches_folder_to_nailgun()

    with patch.applied_patch(
            magic_consts.PUPPET_DIR, *magic_consts.UPGRADE_NODE_PATCHES):
        call_handlers = upgrade_handlers.get_nodes_handlers(
            nodes, env, isolated, live_migration)
        call_handlers('preupgrade')
        call_handlers('prepare')
        env_util.move_nodes(env, nodes)
        if network_template:
            env_util.set_network_template(env, network_template)
        call_handlers('predeploy')
        if isolated or len(nodes) == 1:
            env_util.deploy_nodes(env, nodes)
        else:
            env_util.deploy_changes(env, nodes)
        call_handlers('postdeploy')


def copy_patches_folder_to_nailgun():
    dest_folder = '/tmp'
    folder = os.path.join(magic_consts.CWD, 'patches')
    docker.put_files_to_docker('nailgun', dest_folder, folder)


class UpgradeNodeCommand(cmd.Command):
    """Move nodes to environment and upgrade the node"""

    def get_parser(self, prog_name):
        parser = super(UpgradeNodeCommand, self).get_parser(prog_name)
        parser.add_argument(
            '--isolated', action='store_true',
            help="Isolate node's network from original cluster")
        parser.add_argument(
            '--template', type=str, metavar='TEMPLATE_FILE',
            help="Use network template from file")
        parser.add_argument(
            'env_id', type=int, metavar='ENV_ID',
            help="ID of target environment")
        parser.add_argument(
            'node_ids', type=int, metavar='NODE_ID', nargs='+',
            help="IDs of nodes to be moved")
        parser.add_argument(
            '--no-live-migration',
            action='store_false',
            dest="live_migration",
            default=True,
            help="Run migration on ceph-osd or compute nodes in one command. "
                 "It can prevent to cluster downtime on deploy period. "
                 "(default: True).")
        return parser

    def take_action(self, parsed_args):
        upgrade_node(parsed_args.env_id, parsed_args.node_ids,
                     isolated=parsed_args.isolated,
                     network_template=parsed_args.template,
                     live_migration=parsed_args.live_migration)
