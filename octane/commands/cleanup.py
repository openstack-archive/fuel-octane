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
from oslo_serialization import jsonutils

from octane import magic_consts
from octane.util import env as env_util
from octane.util import ssh

LOG = logging.getLogger(__name__)


def get_access_data(astute):
    return astute['access']


def get_auth_url(astute):
    template = "http://{0}:5000/v2.0/"
    return template.format(
        astute['network_metadata']['vips']['management']['ipaddr'])


def cleanup_environment(env_id):
    cleaning_data = {}
    env = objects.Environment(env_id)
    astute = env_util.get_astute_yaml(env)

    access_data = get_access_data(astute)
    access_data['auth_url'] = get_auth_url(astute)

    roles = ["controller", "compute"]
    hosts = [node.data['fqdn'] for node in env_util.get_nodes(env, roles)]

    cleaning_data['access'] = access_data
    cleaning_data['hosts'] = hosts

    controller = env_util.get_one_controller(env)
    sftp = ssh.sftp(controller)

    script_filename = 'clean_env.py'
    script_dst_filename = '/tmp/{0}'.format(script_filename)
    data_filename = '/tmp/clean_conf.json'

    sftp.put(
        os.path.join(magic_consts.CWD, "helpers/{0}".format(script_filename)),
        script_dst_filename,
    )
    with sftp.open(data_filename, 'w') as data_file:
        data_file.write(jsonutils.dumps(cleaning_data))

    ssh.call(['python', script_dst_filename,
              data_filename], node=controller)

    ssh.call(['rm', '-f', script_dst_filename], node=controller)
    ssh.call(['rm', '-f', data_filename], node=controller)


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
