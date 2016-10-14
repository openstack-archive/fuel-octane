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

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import release as release_obj

from octane.handlers import check

LOG = logging.getLogger(__name__)


def check_runner(env_id, release_id, functional, health, requirements):
    env = environment_obj.Environment(env_id)
    release = release_obj.Release(release_id)
    # Build chain of checks
    check_chain = []
    if functional:
        check_chain.extend(check.FUNCTIONAL_CHECKS)
    if health:
        check_chain.extend(check.HEALTH_CHECKS)
    if requirements:
        check_chain.extend(check.REQUIREMENTS_CHECKS)
    for check_function in check_chain:
        check_function(env=env, release=release)


class CheckCommand(cmd.Command):
    """Migrate and upgrade state databases data"""

    def get_parser(self, prog_name):
        parser = super(CheckCommand, self).get_parser(prog_name)
        parser.add_argument(
            'env_id', type=int, metavar='ENV_ID',
            help="ID of environment")
        parser.add_argument(
            'release_id', type=int, metavar='RELEASE_ID',
            help="ID of release")

        group = parser.add_argument_group()
        group.add_argument(
            '--requirements',
            action='store_const',
            const=True,
            help="check requirements settings")
        group.add_argument(
            '--health',
            action='store_const',
            const=True,
            help="check health settings")
        group.add_argument(
            '--functional',
            action='store_const',
            const=True,
            help="check functional settings")
        group.add_argument(
            '--all',
            action='store_const',
            const=True,
            help="check all settings")
        return parser

    def take_action(self, parsed_args):
        # Execute alternative approach if requested
        any_flags = any([parsed_args.functional,
                         parsed_args.health,
                         parsed_args.requirements])

        if parsed_args.all and any_flags:
            raise Exception(
                "You shouldn't setup --all flag if you set up one "
                "of flags from list [--functional, --health, --requirements]")
        all_flags = not any_flags
        functional = parsed_args.functional or all_flags
        health = parsed_args.health or all_flags
        requirements = parsed_args.requirements or all_flags
        print (parsed_args.env_id, parsed_args.release_id,
               functional, health, requirements)
        check_runner(parsed_args.env_id, parsed_args.release_id,
                     functional, health, requirements)
