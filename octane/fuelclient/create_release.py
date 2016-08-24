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
from fuelclient.commands import release
from fuelclient.common import data_utils


class CreateUpgradeRelease(release.ReleaseMixIn, base.BaseShowCommand):
    """Update node assignment."""

    handler_uri = '/clusters/{cluster_id}/generate_upgrade_release/' \
                  'from/{release_id}/?$'

    columns = ("id",
               "name",
               "state",
               "operating_system",
               "version")

    def get_parser(self, prog_name):
        parser = super(CreateUpgradeRelease, self).get_parser(prog_name)
        parser.add_argument('env_id',
                            type=str,
                            help='ID of the environment ready fo upgrade.')
        parser.add_argument('release_id',
                            type=str,
                            help='ID of the release which takes place upgrade')
        return parser

    def take_action(self, parsed_args):
        data = self.client._entity_wrapper.connection.post_request(
            "clusters/{0}/upgrade/assign".format(parsed_args.env_id))
        return (self.columns,
                data_utils.get_display_data_single(self.columns, data))
