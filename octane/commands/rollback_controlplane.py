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
from cliff import command as cmd
from fuelclient.objects import environment as environment_obj

from octane.util import env as env_util
from octane.util import maintenance
from octane.util import network


def rollback_control_plane(seed_id, orig_id):
    seed_env = environment_obj.Environment(seed_id)
    orig_env = environment_obj.Environment(orig_id)
    # switch physical networks connectivity to orig_env
    roles = ['primary-controller', 'controller']
    for node, info in env_util.iter_deployment_info(seed_env, roles):
        network.delete_patch_ports(node, info)
    for node, info in env_util.iter_deployment_info(orig_env, roles):
        network.create_patch_ports(node, info)
    # enable cluster's services for orig_env
    maintenance.start_cluster(orig_env)
    maintenance.start_corosync_services(orig_env)
    maintenance.enable_apis(orig_env)


class RollbackControlPlaneCommand(cmd.Command):
    """Rollback control plane to the orig environment"""

    def get_parser(self, prog_name):
        parser = super(RollbackControlPlaneCommand, self).get_parser(prog_name)
        parser.add_argument(
            'seed_id', type=int, metavar='SEED_ID',
            help="ID of seed environment")
        parser.add_argument(
            'orig_id', type=int, metavar='ORIG_ID',
            help="ID of original environment")
        return parser

    def take_action(self, parsed_args):
        rollback_control_plane(parsed_args.seed_id, parsed_args.orig_id)
