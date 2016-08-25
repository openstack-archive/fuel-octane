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
from fuelclient.commands import release
from octane.util import fuel_client


class CreateUpgradeRelease(cmd.Command):
    """Clone release and translate settings from the given cluster."""

    columns = release.ReleaseList.columns

    def get_parser(self, prog_name):
        parser = super(CreateUpgradeRelease, self).get_parser(prog_name)
        parser.add_argument('env_id',
                            type=str,
                            help='ID of the environment ready for upgrade.')
        parser.add_argument('release_id',
                            type=str,
                            help='ID of the base release to create a suitable '
                                 'for upgrade release')
        return parser

    def take_action(self, parsed_args):
        data = fuel_client.upgrade_release(
            parsed_args.env_id, parsed_args.release_id)
        return data['id']
