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

import json
import logging
import uuid

from octane.util import subprocess

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import release as release_obj

LOG = logging.getLogger(__name__)


def find_release(operating_system, version):
    for release in release_obj.Release.get_all():
        if release.data['operating_system'] == operating_system and \
                release.data['version'] == version:
            return release
    else:
        raise Exception("Release not found for os %s and version %s",
                        operating_system, version)


def set_cobbler_provision(env_id):
    env = environment_obj.Environment(env_id)
    settings = env.get_settings_data()
    settings["editable"]["provision"]["method"]["value"] = "cobbler"
    env.set_settings_data(settings)


def upgrade_env(orig_id):
    target_release = find_release("Ubuntu", "2014.2.2-6.1")
    LOG.info("Cloning env %s for release %s",
             orig_id, target_release.data['name'])
    res, _ = subprocess.call(
        ["fuel2", "env", "clone", "-f", "json",
         str(orig_id), uuid.uuid4().hex, str(target_release.data['id'])],
        stdout=subprocess.PIPE,
    )
    for kv in json.loads(res):
        if kv['Field'] == 'id':
            seed_id = kv['Value']
            break
    else:
        raise Exception("Couldn't find new environment ID in fuel CLI output:"
                        "\n%s" % res)

    return seed_id


class UpgradeEnvCommand(cmd.Command):
    def get_parser(self, prog_name):
        parser = super(UpgradeEnvCommand, self).get_parser(prog_name)
        parser.add_argument('orig_id', type=int, metavar='ORIG_ID')
        return parser

    def take_action(self, parsed_args):
        seed_id = upgrade_env(parsed_args.orig_id)
        print(seed_id)  # TODO: This shouldn't be needed
        set_cobbler_provision(seed_id)
