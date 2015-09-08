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
import os

from cliff import command as cmd
from fuelclient import objects

from octane import magic_consts
from octane.util import env as env_util
from octane.util import ssh

LOG = logging.getLogger(__name__)


def cleanup_environment(env_id):
    env = objects.Environment(env_id)

    controller = env_util.get_one_controller(env)
    sftp = ssh.sftp(controller)
    admin_pass = env_util.get_admin_password(env, controller)
    script_filename = 'clean_env.py'

    with ssh.tempdir(controller) as tempdir:
        script_src_filename = os.path.join(
            magic_consts.CWD, "helpers", script_filename)
        script_dst_filename = os.path.join(tempdir, script_filename)
        sftp.put(script_src_filename, script_dst_filename)

        command = [
            'sh', '-c', '. /root/openrc; export OS_PASSWORD={0}; python {1}'
            .format(admin_pass, script_dst_filename),
        ]

        data = ""
        for node in env_util.get_controllers(env):
            data = data + node.data['fqdn'] + "\n"
        for node in env_util.get_nodes(env, ['compute']):
            data = data + node.data['hostname'] + "\n"

        with ssh.popen(command, node=controller, stdin=ssh.PIPE) as proc:
            proc.stdin.write(data)


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
