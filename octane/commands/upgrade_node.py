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

from collections import defaultdict
import logging
import os.path

from cliff import command as cmd
from distutils import version
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj

from octane.handlers import upgrade as upgrade_handlers
from octane.helpers import disk
from octane import magic_consts
from octane.util import docker
from octane.util import env as env_util

LOG = logging.getLogger(__name__)


def upgrade_node(env_id, node_ids, isolated=False,
                 network_template=None, disable_life_migration=False):
    # From check_deployment_status
    env = environment_obj.Environment(env_id)
    nodes = [node_obj.Node(node_id) for node_id in node_ids]

    # Sanity check
    one_orig_id = None
    roles = defaultdict(list)
    for node in nodes:
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
        for role in node.data['roles']:
            roles[role].append(node.id)
    if roles['compute'] and roles['controler']:
        raise Exception(
            "You can't upgrade compute and controller in same time."
            "compute nodes are: {compute} \n"
            "controller nodes are: {controller} \n".format(roles)
        )
    if len(roles['compute']) > 1 and not disable_life_migration:
        raise Exception(
            "You can't upgrade nore then 1 compute in same time "
            "compute nodes are: {compute} \n"
            "Mark --disable-life-migration to run this "
            "command on multiple nodes".format(roles)
        )
    if len(roles['ceph-osd']) > 1 and not disable_life_migration:
        raise Exception(
            "You can't upgrade nore then 1 ceph-osd in same time "
            "ceph-osd nodes are: {ceph-osd} \n;"
            "Mark --disable-life-migration to run this "
            "command on multiple nodes".format(roles)
        )

    patch_partition_generator(one_orig_id)
    call_handlers = upgrade_handlers.get_nodes_handlers(
        nodes, env, isolated, disable_life_migration)
    call_handlers('preupgrade')
    call_handlers('prepare')
    env_util.move_nodes(env, nodes)

    # NOTE(aroma): copying of VIPs must be done after node reassignment
    # as according to [1] otherwise the operation will not take any effect
    # [1]: https://bugs.launchpad.net/fuel/+bug/1549254
    env_util.copy_vips(env)

    call_handlers('predeploy')
    if network_template:
        env_util.set_network_template(env, network_template)
    if isolated or len(nodes) == 1:
        env_util.deploy_nodes(env, nodes)
    else:
        env_util.deploy_changes(env, nodes)
    call_handlers('postdeploy')


def patch_partition_generator(env_id):
    """Update partitions generator for releases earlier than 6.0"""

    env = environment_obj.Environment(env_id)
    env_version = version.StrictVersion(env.data["fuel_version"])
    if env_version < version.StrictVersion("6.0"):
        copy_patches_folder_to_nailgun()
        disk.update_partition_generator()


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
            '--disable-life-migration', action='store_true',
            help="Run migration on ceph-osd or compute nodes in one command"
                 "It can prevent to cluster downtime on deploy period")
        return parser

    def take_action(self, parsed_args):
        upgrade_node(parsed_args.env_id, parsed_args.node_ids,
                     isolated=parsed_args.isolated,
                     network_template=parsed_args.template,
                     disable_life_migration=parsed_args.disable_life_migration)
