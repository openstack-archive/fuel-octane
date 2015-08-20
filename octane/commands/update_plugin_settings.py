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

import argparse
import logging
import pyzabbix
import re
import requests
import yaml

from cliff import command as cmd
from fuelclient.objects import environment
from fuelclient.objects import node as node_obj

from octane.commands.upgrade_db import get_controllers
from octane.util import ssh

LOG = logging.getLogger(__name__)


def get_template_hosts_by_name(client, plugin_name):
    return client.template.get(filter={'name': plugin_name},
                               selectHosts=['name'])[0]['hosts']


def get_host_snmp_ip(client, host_id):
    # second type is SNMP type
    return client.hostinterface.get(hosids=host_id,
                                    output=['ip'],
                                    filter={'type': 2})[0]['ip']


def get_zabbix_url(astute):
    return 'http://{0}/zabbix'.format(astute['public_vip'])


def get_zabbix_credentials(astute):
    return astute['zabbix']['username'], astute['zabbix']['password']


def get_astute_yaml(env):
    node = next(get_controllers(env))
    with ssh.sftp(node).open('/etc/astute.yaml') as f:
        data = f.read()
    return yaml.load(data)


def zabbix_monitoring_settings(astute):
    return {'username': {'value': astute['zabbix']['username']},
            'password': {'value': astute['zabbix']['password']},
            'db_password': {'value': astute['zabbix']['db_password']},
            'metadata': {'enabled': astute['zabbix']['enabled']}}


def emc_vnx_settings(astute):
    return {'emc_sp_a_ip': {'value': astute['storage']['emc_sp_a_ip']},
            'emc_sp_b_ip': {'value': astute['storage']['emc_sp_b_ip']},
            'emc_password': {'value': astute['storage']['emc_password']},
            'emc_username': {'value': astute['storage']['emc_username']},
            'emc_pool_name': {'value': astute['storage']['emc_pool_name']},
            'metadata': {'enabled': astute['storage']['volumes_emc']}}


def zabbix_snmptrapd_settings(astute):
    node = node_obj.Node(astute['uid'])
    with ssh.sftp(node).open('/etc/snmp/snmptrapd.conf') as f:
        data = f.read()
    template = re.compile(r"authCommunity\s[a-z-,]+\s([a-z-]+)")
    match = template.search(data)
    return {'community': {'value': match.group(1)},
            'metadata': {'enabled': True}}

def get_zabbix_client(astute):
    url = get_zabbix_url(astute)
    user, password = get_zabbix_credentials(astute)
    session = requests.Session();
    node_cidr = astute['network_scheme']['endpoints']['br-fw-admin']['IP'][0]
    node_ip = node_cidr.split('/')[0]
    session.proxies = {
        'http': 'http://{0}:8888'.format(node_ip)
    }
    client = pyzabbix.ZabbixAPI(server=url, session=session)
    client.login(user=user, password=password)

    return client

def zabbix_monitoring_emc_settings(astute):
    client = get_zabbix_client(astute)

    hosts = get_template_hosts_by_name(client, 'Template EMC VNX')
    for host in hosts:
        host['ip'] = get_host_snmp_ip(client, host['hostid'])
    settings = ','.join(':'.join((host['name'], host['ip'])) for host in hosts)

    return {'hosts': {'value': settings},
            'metadata': {'enabled': True}}


def zabbix_monitoring_extreme_networks_settings(astute):
    client = get_zabbix_client(astute)

    hosts = get_template_hosts_by_name(client, 'Template Extreme Networks')
    for host in hosts:
        host['ip'] = get_host_snmp_ip(client, host['hostid'])
    settings = ','.join(':'.join((host['name'], host['ip'])) for host in hosts)

    return {'hosts': {'value': settings},
            'metadata': {'enabled': True}}


def transfer_plugins_settings(orig_env_id, seed_env_id, plugins):
    orig_env = environment.Environment(orig_env_id)
    seed_env = environment.Environment(seed_env_id)
    astute = get_astute_yaml(orig_env)
    attrs = {}

    for plugin_name in plugins:
        LOG.info("Fetching settings for plugin '%s'", plugin_name)
        plugin = plugin_name.replace('-', '_')
        attrs[plugin] = PLUGINS[plugin_name](astute)

    seed_env.update_attributes({'editable': attrs})


PLUGINS = {
    'zabbix-monitoring': zabbix_monitoring_settings,
    'emc-vnx': emc_vnx_settings,
    'zabbix-snmptrapd': zabbix_snmptrapd_settings,
    'zabbix-monitoring-emc': zabbix_monitoring_emc_settings,
    'zabbix-monitoring-extreme-networks': \
         zabbix_monitoring_extreme_networks_settings,
}

def plugin_names(s):
    plugins = s.split(',')
    for plugin in plugins:
        if plugin not in PLUGINS:
            raise argparse.ArgumentTypeError("Unknown plugin '{0}'"
                                             .format(plugin))
    return plugins


class UpdatePluginSettingsCommand(cmd.Command):
    """Transfer settings for specified plugin from ORIG_ENV to SEED_ENV"""

    def get_parser(self, prog_name):
        parser = super(UpdatePluginSettingsCommand, self).get_parser(prog_name)
        parser.add_argument(
            'orig_env',
            type=int,
            metavar='ORIG_ID',
            help="ID of original environment")
        parser.add_argument(
            'seed_env',
            type=int,
            metavar='SEED_ID',
            help="ID of seed environment")
        parser.add_argument(
            '--plugins',
            type=plugin_names,
            help="Comma separated values: {0}".format(', '.join(PLUGINS)))

        return parser

    def take_action(self, parsed_args):
        transfer_plugins_settings(parsed_args.orig_env,
                                  parsed_args.seed_env,
                                  parsed_args.plugins)
