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
import re
import uuid

from octane.commands.upgrade_db import get_controllers
from octane.util import ssh

from cliff import command as cmd
from fuelclient.objects import environment
import zabbix_client

LOG = logging.getLogger(__name__)


def get_template_hosts_by_name(client, plugin_name):
    return client.template.get(filter={'name': plugin_name},
                               selectHosts=['name'])[0]['hosts']


def get_host_snmp_ip(client, host_id):
    # second type is SNMP type
    return client.hostinterface.get(hosids=host_id,
                                    output=['ip'],
                                    filter={'type': 2})[0]['ip']


def get_zabbix_url(env):
    data = env.get_network_data()
    ip = data['public_vip']
    return 'http://{0}/zabbix'.format(ip)


def get_zabbix_credentials(env):
    # FIXME remove hardcode
    return 'admin', 'Vdzhw1OY'


def transfer_zabbix_snmptrap(orig_env):
    # go to controller and parse /etc/snmp/snmptrapd.conf
    # ACCESS CONTROL sections
    node = next(get_controllers(orig_env))
    data, _ = ssh.call(['cat', '/etc/snmp/snmptrapd.conf'], stdout=ssh.PIPE, node=node)
    template = re.compile(r"authCommunity\s[a-z-,]+\s([a-z-]+)")
    match = template.search(data)
    return {'community': {'value': match.group(1)},
            'metadata': {'enabled': True}}


def transfer_zabbix_monitoring_emc(orig_env):
    url = get_zabbix_url(orig_env)
    user, password = get_zabbix_credentials(orig_env)
    client = zabbix_client.ZabbixServerProxy(url)
    client.user.login(user=user, password=password)
    hosts = get_template_hosts_by_name(client, 'Template EMC VNX')
    for host in hosts:
        host['ip'] = get_host_snmp_ip(client, host['hostid'])
    settings = ','.join(':'.join((host['name'], host['ip'])) for host in hosts)
    return {'hosts': {'value': settings},
            'metadata': {'enabled': True}}


def transfer_zabbix_monitoring_extreme_networks(orig_env):
    url = get_zabbix_url(orig_env)
    user, password = get_zabbix_credentials(orig_env)
    client = zabbix_client.ZabbixServerProxy(url)
    client.user.login(user=user, password=password)
    hosts = get_template_hosts_by_name(client, 'Template Extreme Networks')
    for host in hosts:
        host['ip'] = get_host_snmp_ip(client, host['hostid'])
    settings = ','.join(':'.join((host['name'], host['ip'])) for host in hosts)
    return {'hosts': {'value': settings},
            'metadata': {'enabled': True}}


class UpgradePluginCommand(cmd.Command):
    """Transfer settings for specified plugin from ORIG_ENV to SEED_ENV"""

    def get_parser(self, prog_name):
        parser = super(UpgradePluginCommand, self).get_parser(prog_name)
        parser.add_argument(
            'orig_env', type=int, metavar='ORIG_ID',
            help="ID of original environment")
        parser.add_argument(
            'seed_env', type=int, metavar='SEED_ID',
            help="ID of seed environment")

        parser.add_argument(
            '--zabbix-snmptrap', action='store_true',
            help="Transfer settings for zabbix-snmptrapd plugin")
        parser.add_argument(
            '--zabbix-monitoring-emc', action='store_true',
            help="Transfer settings for zabbix-monitoring-emc plugin")
        parser.add_argument(
            '--zabbix-monitoring-extreme-networks', action='store_true',
            help="Transfer settings for zabbix-monitoring-extreme-networks"
                 "plugins")
        return parser

    def take_action(self, parsed_args):
        orig_env = environment.Environment(parsed_args.orig_env)
        seed_env = environment.Environment(parsed_args.seed_env)
        attrs = {}

        if parsed_args.zabbix_snmptrap:
            attrs['zabbix_snmptrapd'] = transfer_zabbix_snmptrap(
                orig_env)
        if parsed_args.zabbix_monitoring_emc:
            attrs['zabbix_monitoring_emc'] = transfer_zabbix_monitoring_emc(
                orig_env)
        if parsed_args.zabbix_monitoring_extreme_networks:
            attrs['zabbix_monitoring_extreme_networks'] = \
                transfer_zabbix_monitoring_extreme_networks(orig_env)

        seed_env.update_attributes({'editable': attrs})
