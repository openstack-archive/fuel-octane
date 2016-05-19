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

from cliff import command
from fuelclient.client import APIClient
from octane.handlers import backup_restore
from octane import magic_consts
from octane.util import fuel_client

LOG = logging.getLogger(__name__)


def enable_release(release_id, context):
    release_url = "/releases/{0}".format(release_id)
    with fuel_client.set_auth_context(context):
        data = APIClient.get_request(release_url)
        state = data.get('state')
        if state == magic_consts.RELEASE_STATUS_MANAGED:
            data['state'] = magic_consts.RELEASE_STATUS_ENABLED
            APIClient.put_request(release_url, data)
        else:
            LOG.error("Cannot enable release %s: has status %s, not %s",
                      release_id,
                      state,
                      magic_consts.RELEASE_STATUS_MANAGED)


class EnableReleaseCommand(command.Command):

    def get_parser(self, *args, **kwargs):
        parser = super(EnableReleaseCommand, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "--id",
            type=str,
            action="store",
            dest="release_id",
            required=True,
            help="ID of the release to enable.")
        parser.add_argument(
            "--admin-password",
            type=str,
            action="store",
            dest="admin_password",
            required=True,
            help="Fuel admin password")
        return parser

    def get_context(self, parsed_args):
        return backup_restore.NailgunCredentialsContext(
            password=parsed_args.admin_password,
            user="admin"
        )

    def take_action(self, parsed_args):
        assert parsed_args.release_id
        assert parsed_args.admin_password
        enable_release(parsed_args.release_id,
                       self.get_context(parsed_args))
