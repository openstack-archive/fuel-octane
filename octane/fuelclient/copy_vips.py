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


class CopyVIPs(env_commands.EnvMixIn, base.BaseCommand):
    """Copy VIPs to seed cluster"""

    def get_parser(self, prog_name):
        parser = super(CopyVIPs, self).get_parser(prog_name)
        parser.add_argument('env_id',
                            type=str,
                            help='ID of the environment')
        return parser

    def take_action(self, parsed_args):
        # NOTE(aroma): while copying of VIPs procedure is not a part of
        # fuelclient.objects.Environment the connection will be called directly
        self.client._entity_wrapper.connection.post_request(
            "clusters/{0}/upgrade/vips".format(parsed_args.env_id))

        msg = ('VIPs successfully copied from the original cluster to seed '
               'cluster {0}'.format(parsed_args.env_id))
        self.app.stdout.write(msg)
