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


def upgrade_node(seed_id, node_id, isolated=False):
    pass


def isolated_type(s):
    if s != 'isolated':
        raise ValueError(s)
    else:
        return True


class UpgradeNodeCommand(cmd.Command):
    def get_parser(self, prog_name):
        parser = super(UpgradeNodeCommand, self).get_parser(prog_name)
        parser.add_argument('seed_id', type=int, metavar='SEED_ID')
        parser.add_argument('orig_id', type=int, metavar='ORIG_ID')
        parser.add_argument('isolated', type=isolated_type, default=False,
                            nargs='?')
        return parser

    def take_action(self, parsed_args):
        upgrade_node(parsed_args.seed_id, parsed_args.node_id,
                     isolated=parsed_args.isolated)
