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
import os

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj

from octane.util import deployment as deploy
from octane.util import env as env_util
from octane.util import helpers
from octane.util import maintenance
from octane.util import network

LOG = logging.getLogger(__name__)

#
# 1. seed: switch_controlplane_1 (start services)
# 2. orig: switch_controlplane_1 (stop services)

# 2* for node, info in env_util.iter_deployment_info(orig_env, roles):
#     network.delete_patch_ports(node, info)

# 3. seed: switch_controlplane_2 (reconfigure network)
# 4. orig: switch_controlplane_2 (decomission services)
#


def upgrade_control_plane(orig_id, seed_id):
    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)
    controllers = list(env_util.get_controllers(seed_env))
    # enable all services on seed env
    if len(controllers) > 1:
        maintenance.stop_cluster(seed_env)
    else:
        maintenance.start_corosync_services(seed_env)
        maintenance.start_upstart_services(seed_env)
    # disable cluster services on orig env
    maintenance.stop_cluster(orig_env)
    # switch networks to seed env
    roles = ['primary-controller', 'controller']
    # disable physical connectivity for orig env
    for node, info in env_util.iter_deployment_info(orig_env, roles):
        network.delete_patch_ports(node, info)
    # enable physical connectivity for seed env
    for node, info in env_util.iter_deployment_info(seed_env, roles):
        network.delete_overlay_networks(node, info)
        network.create_patch_ports(node, info)
    # enable all services on seed env
    if len(controllers) > 1:
        maintenance.start_cluster(seed_env)
        maintenance.start_corosync_services(seed_env)
        maintenance.start_upstart_services(seed_env)


def upgrade_control_plane_with_graph(orig_id, seed_id):
    """Switch controlplane using deployment graphs"""

    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)

    deploy.upload_graphs(orig_id, seed_id)

    try:
        # Start openstack services on the seed controller
        deploy.execute_graph_and_wait('switch-control-1', seed_id)

        # Kill pacemaker on the original controllers
        deploy.execute_graph_and_wait('switch-control-1', orig_id)

        # Cut off the original controller from network
        roles = ['primary-controller', 'controller']
        for node, info in env_util.iter_deployment_info(orig_env, roles):
            network.delete_patch_ports(node, info)

        # TODO(pchechetin): Restore transformation for the environment
        backup_path = env_util.get_dir_deployment_info(seed_id)
        for node, info in env_util.iter_deployment_info(seed_env, roles):
            fname = os.path.join(
                backup_path,
                "{0}.yaml".format(info['uid']))

            deployment_info = helpers.load_yaml(fname)

            seed_env.upload_facts('deployment', deployment_info)

        # Connect the seed controller to a physical network
        deploy.execute_graph_and_wait('switch-control-2', seed_id)

        # Decommission the orig controllers by stopping OpenStack services
        deploy.execute_graph_and_wait('switch-control-2', orig_id)

    except Exception:
        # TODO(pchechetin): Delete this `raise` when applying of the rollback
        #                   won't be failing all the time.
        raise

        # TODO(pchechetin): Disconnect the orig controller
        #                   Connect the seed controller
        LOG.info('Trying to rollback switch-control phase')

        deploy.execute_graph_and_wait('switch-control-rollback', orig_id)
        deploy.execute_graph_and_wait('switch-control-rollback', seed_id)
        raise


class UpgradeControlPlaneCommand(cmd.Command):
    """Switch control plane to the seed environment"""

    def get_parser(self, prog_name):
        parser = super(UpgradeControlPlaneCommand, self).get_parser(prog_name)
        parser.add_argument(
            'orig_id', type=int, metavar='ORIG_ID',
            help="ID of original environment")
        parser.add_argument(
            'seed_id', type=int, metavar='SEED_ID',
            help="ID of seed environment")
        parser.add_argument(
            '--with-graph', action='store_true',
            help='EXPERIMENTAL: Use Fuel deployment graphs'
                 ' instead of python-based commands.')
        return parser

    def take_action(self, parsed_args):
        if parsed_args.with_graph:
            upgrade_control_plane_with_graph(
                parsed_args.orig_id,
                parsed_args.seed_id)
        else:
            upgrade_control_plane(parsed_args.orig_id, parsed_args.seed_id)
