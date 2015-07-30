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

import os.path
import time

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj

from octane import magic_consts
from octane.util import ssh


def delete_fuel_resources(seed_env):
    for node in node_obj.Node.get_all():
        if node.data['cluster'] != seed_env.data['id']:
            continue
        if 'controller' in node.data['roles']:
            break
    else:
        raise Exception("Can't find controller node in env %s" %
                        seed_env.data['id'])
    sftp = ssh.sftp(node)
    sftp.put(
        os.path.join(magic_consts.CWD, "helpers/delete_fuel_resources.py"),
        "/tmp/delete_fuel_resources.py",
    )
    ssh.call(
        ["sh", "-c", ". /root/openrc; python /tmp/delete_fuel_resources.py"],
        node=node,
    )


def upgrade_db(orig_id, seed_id):
    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)
    delete_fuel_resources(seed_env)


class UpgradeDBCommand(cmd.Command):
    """Migrate and upgrade state databases data"""

    def get_parser(self, prog_name):
        parser = super(UpgradeDBCommand, self).get_parser(prog_name)
        parser.add_argument(
            'orig_id', type=int, metavar='ORIG_ID',
            help="ID of original environment")
        parser.add_argument(
            'seed_id', type=int, metavar='SEED_ID',
            help="ID of seed environment")
        return parser

    def take_action(self, parsed_args):
        upgrade_db(parsed_args.orig_id, parsed_args.seed_id)
