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
from fuelclient import objects

from octane.util import env as env_util
from octane.util import node as node_util
from octane.util import nova


def clean_services_for_node(controller, node):
    services_stdout = nova.run_nova_cmd(
        ["nova", "service-list", "--host", node.data['hostname']],
        controller)
    services = nova.nova_stdout_parser(services_stdout)
    for service in services:
        nova.run_nova_cmd(
            ["nova", "service-delete", service['Id']], controller,
            output=False)


def cleanup_environment(env_id):
    env = objects.Environment(env_id)
    controller = env_util.get_one_controller(env)

    nodes = env_util.get_nodes(env, ['controller', 'compute'])
    for node in nodes:
        node_util.remove_compute_upgrade_levels(node)
        node_util.restart_nova_services(node)
        clean_services_for_node(controller, node)

    env_util.cleanup(env_id)


class CleanupCommand(cmd.Command):
    """Cleanup upgraded environment"""

    def get_parser(self, prog_name):
        parser = super(CleanupCommand, self).get_parser(prog_name)

        parser.add_argument(
            'env', type=int, metavar='ENV_ID',
            help="ID of environment to cleanup")
        return parser

    def take_action(self, parsed_args):
        cleanup_environment(parsed_args.env)
