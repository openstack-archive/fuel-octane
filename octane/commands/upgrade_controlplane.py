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
import os
import subprocess
import yaml

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj

from octane.helpers import network
from octane import magic_consts
from octane.util import env as env_util
from octane.util import maintenance
from octane.util import ssh


def start_corosync_services(env):
    node = next(env_util.get_controllers(env))
    status_out = ssh.call_output(['cibadmin', '--query', '--scope',
                                  'resources'], node=node)
    for service in maintenance.get_crm_services(status_out):
        while True:
            try:
                ssh.call(['crm', 'resource', 'start', service],
                         node=node)
            except subprocess.CalledProcessError:
                pass
            else:
                break


def start_upstart_services(env):
    controllers = list(env_util.get_controllers(env))
    for node in controllers:
        sftp = ssh.sftp(node)
        try:
            svc_file = sftp.open('/root/services_list')
        except IOError:
            raise
        else:
            with svc_file:
                to_start = svc_file.read().splitlines()
        for service in to_start:
            ssh.call(['start', service], node=node)


def disconnect_networks(env):
    controllers = list(env_util.get_controllers(env))
    for node in controllers:
        deployment_info = env_util.get_astute_yaml(env, node)
        network.delete_patch_ports(node, deployment_info)


def connect_to_networks(env):
    deployment_info = []
    controllers = list(env_util.get_controllers(env))
    backup_path = os.path.join(magic_consts.FUEL_CACHE,
                               'deployment_{0}.orig'
                               .format(env.id))
    for filename in os.listdir(backup_path):
        filepath = os.path.join(backup_path, filename)
        with open(filepath) as info_file:
            info = yaml.safe_load(info_file)
            deployment_info.append(info)
    for node in controllers:
        for info in deployment_info:
            if (info['role'] in ('primary-controller', 'controller')
                    and info['uid'] == str(node.id)):
                network.delete_overlay_networks(node, info)
                network.create_patch_ports(node, info)


def update_neutron_config(orig_env, seed_env):
    controllers = list(env_util.get_controllers(seed_env))
    tenant_file = '%s/env-%s-service-tenant-id' % (magic_consts.FUEL_CACHE,
                                                   str(orig_env.data['id']))
    with open(tenant_file) as f:
        tenant_id = f.read()

    sed_script = 's/^(nova_admin_tenant_id )=.*/\\1 = %s/' % (tenant_id,)
    for node in controllers:
        ssh.call(['sed', '-re', sed_script, '-i', '/etc/neutron/neutron.conf'],
                 node=node)


def upgrade_control_plane(orig_id, seed_id):
    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)
    update_neutron_config(orig_env, seed_env)
    start_corosync_services(seed_env)
    start_upstart_services(seed_env)
    disconnect_networks(orig_env)
    connect_to_networks(seed_env)


class UpgradeControlPlaneCommand(cmd.Command):
    """Switch control plane to the seed environment"""

    def get_parser(self, prog_name):
        parser = super(UpgradeControlPlaneCommand, self).get_parser(prog_name)
        parser.add_argument(
            'orig_id', type=int, metavar='ORIG_ID',
            help="ID of original environment")
        parser.add_argument(
            'seed_id', type=int, metavar='SEED_ID',
            help="ID of seed environment")
        return parser

    def take_action(self, parsed_args):
        upgrade_control_plane(parsed_args.orig_id, parsed_args.seed_id)
