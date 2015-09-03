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

from __future__ import print_function

import logging

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import release as release_obj

from octane import magic_consts
from octane.util import env as env_util
from octane.util import ssh

LOG = logging.getLogger(__name__)


def find_release(operating_system, version):
    for release in release_obj.Release.get_all():
        if release.data['operating_system'] == operating_system and \
                release.data['version'] == version:
            return release
    else:
        raise Exception("Release not found for os %s and version %s",
                        operating_system, version)


def find_deployable_release(operating_system):
    for release in release_obj.Release.get_all():
        if release.data['operating_system'] == operating_system and \
                release.data['is_deployable']:
            return release
    else:
        raise Exception("Deployable release not found for os %s",
                        operating_system)


def set_cobbler_provision(env_id):
    env = environment_obj.Environment(env_id)
    settings = env.get_settings_data()
    settings["editable"]["provision"]["method"]["value"] = "cobbler"
    env.set_settings_data(settings)


def upgrade_env(env_id):
    target_release = find_deployable_release("Ubuntu")
    seed_id = env_util.clone_env(env_id, target_release)
    env_util.change_env_settings(seed_id)
    return seed_id


def write_service_tenant_id(env_id):
    env = environment_obj.Environment(env_id)
    node = env_util.get_one_controller(env)
    tenant_id, _ = ssh.call(["bash", "-c", ". /root/openrc;",
                             "keystone tenant-list | ",
                             "awk -F\| '\$2 ~ /id/{print \$3}' | tr -d \ "],
                            stdout=ssh.PIPE,
                            node=node)
    tenant_file = '%s/env-%s-service-tenant-id' % (magic_consts.FUEL_CACHE,
                                                   str(env_id))
    with open(tenant_file, 'w') as f:
        f.write(tenant_id)


class UpgradeEnvCommand(cmd.Command):
    """Create upgrade seed env for env ENV_ID and copy settings to it"""

    def get_parser(self, prog_name):
        parser = super(UpgradeEnvCommand, self).get_parser(prog_name)
        parser.add_argument(
            'env_id', type=int, metavar='ENV_ID',
            help="ID of environment to be upgraded")
        return parser

    def take_action(self, parsed_args):
        write_service_tenant_id(parsed_args.env_id)
        seed_id = upgrade_env(parsed_args.env_id)
        print(seed_id)  # TODO: This shouldn't be needed
