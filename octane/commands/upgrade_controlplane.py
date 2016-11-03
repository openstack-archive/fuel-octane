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

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj

from octane.util import deployment as deploy
from octane.util import env as env_util
from octane.util import maintenance
from octane.util import network

LOG = logging.getLogger(__name__)


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
    # NOTE(akscram): Remove replaced deployment info with
    # the isolation mode and the alternative gateway.
    # CAUTION: This method removes replaced deployment
    # information for all nodes in an environment.
    seed_env.delete_facts("deployment")


def add_upgrade_attrs_to_settings(orig_env, seed_env):
    upgrade_hash = {
        'relation_info': {
            'orig_cluster_version': orig_env.data['fuel_version'],
            'seed_cluster_version': seed_env.data['fuel_version']
        }
    }

    orig_attrs = orig_env.get_settings_data()
    orig_upgrade = orig_attrs['editable']['common'].get('upgrade', {})
    orig_upgrade.update(upgrade_hash)
    orig_attrs['editable']['common']['upgrade'] = orig_upgrade
    orig_env.set_settings_data(orig_attrs)

    seed_attrs = seed_env.get_settings_data()
    seed_upgrade = seed_attrs['editable']['common'].get('upgrade', {})
    seed_upgrade.update(upgrade_hash)
    seed_attrs['editable']['common']['upgrade'] = seed_upgrade
    seed_env.set_settings_data(seed_attrs)


def upgrade_control_plane_with_graph(orig_id, seed_id):
    """Switch controlplane using deployment graphs"""

    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)
    add_upgrade_attrs_to_settings(orig_env, seed_env)

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

        # Restore transformations for the seed environment
        seed_env.delete_facts("deployment")

        # Connect the seed controller to a physical network
        deploy.execute_graph_and_wait('switch-control-2', seed_id)

        # Decommission the orig controllers by stopping OpenStack services
        deploy.execute_graph_and_wait('switch-control-2', orig_id)
    except Exception:
        LOG.info('Trying to rollback switch-control phase')

        # Cut off the seed controller from networks
        roles = ['primary-controller', 'controller']

        for info in seed_env.get_default_facts('deployment'):
            if set(info['roles']) & set(roles):
                network.delete_patch_ports(node_obj.Node(info['uid']), info)

        # Restore network connectivity for the original controller
        # Recreate cluster
        deploy.execute_graph_and_wait('switch-control-rollback', orig_id)

        # Stop openstack services on the seed controller
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
