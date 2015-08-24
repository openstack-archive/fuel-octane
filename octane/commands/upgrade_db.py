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
import shutil
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
        if ('controller' in node.data['roles'] or
                'controller' in node.data['pending_roles']):
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


def mysqldump_from_env(env):
    node = next(get_controllers(env))
    local_fname = os.path.join(magic_consts.FUEL_CACHE, 'dbs.original.sql.gz')
    with ssh.popen(['sh', '-c', 'mysqldump --add-drop-database'
                    ' --lock-all-tables --databases %s | gzip' %
                    (' '.join(magic_consts.OS_SERVICES),)],
                   stdout=ssh.PIPE, node=node) as proc:
        with open(local_fname, 'wb') as local_file:
            shutil.copyfileobj(proc.stdout, local_file)
    local_fname2 = os.path.join(
        magic_consts.FUEL_CACHE,
        'dbs.original.cluster_%s.sql.gz' % (env.data['id'],),
    )
    shutil.copy(local_fname, local_fname2)
    return local_fname


def mysqldump_restore_to_env(env, fname):
    node = next(get_controllers(env))
    with open(fname, 'rb') as local_file:
        with ssh.popen(['sh', '-c', 'zcat | mysql'],
                       stdin=ssh.PIPE, node=node) as proc:
            shutil.copyfileobj(local_file, proc.stdin)


def db_sync(env):
    node = next(get_controllers(env))
    ssh.call(['keystone-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(['nova-manage', 'db', 'sync'], node=node, parse_levels=True)
    ssh.call(['heat-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(['glance-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(['neutron-db-manage', '--config-file=/etc/neutron/neutron.conf',
              'upgrade', 'head'], node=node, parse_levels='^(?P<level>[A-Z]+)')
    ssh.call(['cinder-manage', 'db', 'sync'], node=node, parse_levels=True)


def upgrade_db(orig_id, seed_id):
    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)
    delete_fuel_resources(seed_env)
    # Wait for Neutron to reconfigure networks
    time.sleep(7)  # FIXME: Use more deterministic way
    disable_apis(orig_env)
    stop_corosync_services(seed_env)
    stop_upstart_services(seed_env)
    fname = mysqldump_from_env(orig_env)
    mysqldump_restore_to_env(seed_env, fname)
    db_sync(seed_env)


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
