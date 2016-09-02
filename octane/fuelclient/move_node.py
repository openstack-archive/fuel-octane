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

from fuelclient.commands import base
from fuelclient.commands import environment as env_commands


class EnvMoveNode(env_commands.EnvMixIn, base.BaseCommand):
    """Update node assignment."""

    def get_parser(self, prog_name):
        parser = super(EnvMoveNode, self).get_parser(prog_name)
        parser.add_argument('--no-provision', dest='provision',
                            default=True, action='store_false',
                            help="Do not perform reprovisioning of the node.")
        parser.add_argument('--roles', nargs='?',
                            help="Assign the given roles to the node (a comma "
                                 "separated list of roles).")
        parser.add_argument('env_id',
                            type=str,
                            help='ID of the environment.')
        parser.add_argument('nodes_ids',
                            type=int,
                            metavar='node-id',
                            nargs='+',
                            help='IDs of the nodes to upgrade.')
        return parser

    def take_action(self, parsed_args):
        # TODO(akscram): While the clone procedure is not a part of
        #                fuelclient.objects.Environment the connection
        #                will be called directly.
        data = {
            'nodes_ids': parsed_args.nodes_ids,
            'reprovision': parsed_args.provision,
        }
        if parsed_args.roles:
            data['roles'] = parsed_args.roles.split(',')
        self.client._entity_wrapper.connection.post_request(
            "clusters/{0}/upgrade/assign".format(parsed_args.env_id),
            data,
        )
        msg = ('Nodes {nodes_ids} successfully relocated to the environment'
               ' {env_id}.\n'.format(
                   nodes_ids=parsed_args.nodes_ids,
                   env_id=parsed_args.env_id,
               ))
        self.app.stdout.write(msg)
