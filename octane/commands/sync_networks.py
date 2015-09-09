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
from fuelclient import objects
from requests import HTTPError

from octane.util import env as env_util

LOG = logging.getLogger(__name__)

KEEP_NETWORK_NAMES = ['fuelweb_admin', 'management', 'public']


def update_env_networks(env_id, networks):
    fields_to_update = ['meta', 'ip_ranges']
    env = objects.Environment(env_id)
    release_id = env.get_fresh_data()['release_id']
    network_data = env.get_network_data()
    node_group_id = None

    for ng in network_data['networks']:
        if ng['name'] in KEEP_NETWORK_NAMES:
            continue
        if node_group_id is None:
            # for now we'll have only one node group
            # so just take it id from any network
            node_group_id = ng['group_id']
        objects.NetworkGroup(ng['id']).delete()

    data_to_update = {}
    for ng in networks:
        if ng['name'] in KEEP_NETWORK_NAMES:
            continue
        try:
            objects.NetworkGroup.create(
                ng['name'],
                release_id,
                ng['vlan_start'],
                ng['cidr'],
                ng['gateway'],
                node_group_id,
                ng['meta']
            )
        except HTTPError:
            LOG.error("Cannot sync network '{0}'".format(ng['name']))
            continue
        data = {}
        for key in fields_to_update:
            data[key] = ng[key]
        data_to_update[ng['name']] = data

    # now we need to update new networks with
    # correct ip_ranges and meta
    network_data = env.get_network_data()
    network_data['networks'] = [ng for ng in network_data['networks']
                                if ng['name'] not in KEEP_NETWORK_NAMES]
    for ng in network_data['networks']:
        if ng['name'] in data_to_update:
            for k in fields_to_update:
                ng[k] = data_to_update[ng['name']][k]
    env.set_network_data(network_data)


class SyncNetworksCommand(cmd.Command):
    """Synchronize network groups in original and seed environments"""

    def get_parser(self, prog_name):
        parser = super(SyncNetworksCommand, self).get_parser(prog_name)
        parser.add_argument(
            'original_env', type=int, metavar='ORIGINAL_ENV_ID',
            help="ID of original environment")
        parser.add_argument(
            'seed_env', type=int, metavar='SEED_ENV_ID',
            help="ID of seed environment")
        return parser

    def take_action(self, parsed_args):
        orig_env = objects.Environment(parsed_args.original_env)
        networks = env_util.get_env_networks(orig_env)
        update_env_networks(parsed_args.seed_env, networks)
