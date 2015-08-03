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
import re
import time

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj

from octane import magic_consts
from octane.util import ssh


def get_controllers(env):
    found = False
    for node in node_obj.Node.get_all():
        if node.data['cluster'] != env.data['id']:
            continue
        if 'controller' in node.data['roles']:
            yield node
            found = True
    if not found:
        raise Exception("Can't find controller node in env %s" %
                        env.data['id'])


def delete_fuel_resources(seed_env):
    node = next(get_controllers(seed_env))
    sftp = ssh.sftp(node)
    sftp.put(
        os.path.join(magic_consts.CWD, "helpers/delete_fuel_resources.py"),
        "/tmp/delete_fuel_resources.py",
    )
    ssh.call(
        ["sh", "-c", ". /root/openrc; python /tmp/delete_fuel_resources.py"],
        node=node,
    )


def disable_apis(env):
    controllers = list(get_controllers(env))
    maintenance_line = 'backend maintenance'
    stats_socket_re = re.compile('stats\s+socket\s+/var/lib/haproxy/stats'
                                 '(?!.*level admin)')
    mode_tcp_re = re.compile('mode\s+tcp')
    use_backend_line = '  use_backend maintenance if TRUE'
    for node in controllers:
        sftp = ssh.sftp(node)
        sftp.chdir('/etc/haproxy')
        with ssh.update_file(sftp, 'haproxy.cfg') as (old, new):
            found_maint_line = False
            for line in old:
                if maintenance_line in line:
                    found_maint_line = True
                line = stats_socket_re.sub(r'\g<0> level admin', line)
                new.write(line)
            if not found_maint_line:
                new.write(maintenance_line)
        sftp.chdir('/etc/haproxy/conf.d')
        for f in sftp.listdir():
            with ssh.update_file(sftp, f) as (old, new):
                contents = old.read()
                if not mode_tcp_re.search(contents):
                    raise ssh.DontUpdateException
                new.write(contents)
                if not contents.endswith('\n'):
                    new.write('\n')
                new.write(use_backend_line)
        ssh.call(['crm', 'resource', 'restart', 'p_haproxy'], node=node)

_default_exclude_services = ('mysql', 'haproxy', 'p_dns', 'p_ntp')


def parse_crm_status(status_out, exclude=_default_exclude_services):
    for match in re.finditer(r"clone.*\[(.*)\]", status_out):
        name = match.group(1)
        if any(service in name for service in exclude):
            continue
        yield name


def stop_corosync_services(env):
    controllers = list(get_controllers(env))
    for node in controllers:
        status_out, _ = ssh.call(['crm', 'status'], stdout=ssh.PIPE, node=node)
        for service in parse_crm_status(status_out):
            ssh.call(['crm', 'resource', 'stop', service], node=node)


def stop_upstart_services(env):
    controllers = list(get_controllers(env))
    service_re = re.compile("^((?:%s)[^\s]*).*start/running" %
                            ("|".join(magic_consts.OS_SERVICES),),
                            re.MULTILINE)
    for node in controllers:
        sftp = ssh.sftp(node)
        try:
            svc_file = sftp.open('/root/services_list')
        except IOError:
            with sftp.open('/root/services_list.tmp', 'w') as svc_file:
                initctl_out, _ = ssh.call(['initctl', 'list'],
                                          stdout=ssh.PIPE, node=node)
                to_stop = []
                for match in service_re.finditer(initctl_out):
                    service = match.group(1)
                    to_stop.append(service)
                    svc_file.write(service + '\n')
            sftp.rename('/root/services_list.tmp', '/root/services_list')
        else:
            with svc_file:
                to_stop = svc_file.read().splitlines()
        for service in to_stop:
            ssh.call(['stop', service], node=node)


def upgrade_db(orig_id, seed_id):
    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)
    delete_fuel_resources(seed_env)
    # Wait for Neutron to reconfigure networks
    time.sleep(7)  # FIXME: Use more deterministic way
    disable_apis(orig_env)
    stop_corosync_services(seed_env)
    stop_upstart_services(seed_env)


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
