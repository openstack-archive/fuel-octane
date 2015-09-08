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


class CloneIPs(env_commands.EnvMixIn, base.BaseCommand):
    """Clone IPs from original environment controllers to seed environment"""

    def get_parser(self, prog_name):
        parser = super(CloneIPs, self).get_parser(prog_name)
        parser.add_argument('id', type=int,
                            help='ID of environment to clone from')
        parser.add_argument('--networks',
                            type=str,
                            nargs='+',
                            help='Names of networks which ips should'
                                 ' be copied.')
        return parser

    def take_action(self, parsed_args):
        # TODO(asvechnikov): While the clone ip procedure is not a part of
        #                    fuelclient.objects.Environment the connection
        #                    will be called directly.
        networks = []
        if parsed_args.networks:
            networks = parsed_args.networks
        self.client._entity_wrapper.connection.post_request(
            "clusters/{0}/upgrade/clone_ips".format(parsed_args.id),
            {'networks': networks}
        )
