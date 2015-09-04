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
from octane.helpers.sync_glance_images import sync_glance_images


class SyncImagesCommand(cmd.Command):
    """Sync glance images between ORIG and SEED environments"""

    def get_parser(self, prog_name):
        parser = super(SyncImagesCommand, self).get_parser(prog_name)
        parser.add_argument(
            'orig_id', type=int, metavar='ORIG_ID',
            help="ID of original environment")
        parser.add_argument(
            'seed_id', type=int, metavar='SEED_ID',
            help="ID of seed environment")
        parser.add_argument(
            'swift_ep', type=str,
            help="Endpoint's name where swift-proxy service is listening on")
        return parser

    def take_action(self, parsed_args):
        sync_glance_images(parsed_args.orig_id, parsed_args.seed_id,
                           parsed_args.swift_ep)
