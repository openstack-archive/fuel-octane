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

import shutil

from octane.util import env as env_util
from octane.util import ssh


def get_databases(env):
    node = env_util.get_one_controller(env)
    with ssh.popen(
            ['mysql', '--batch', '--skip-column-names'],
            stdin=ssh.PIPE, stdout=ssh.PIPE, node=node) as proc:
        proc.stdin.write('SHOW DATABASES')
        out = proc.communicate()[0]
    return out.splitlines()


def mysqldump_from_env(env, role_name, dbs, fname):
    node = env_util.get_one_node_of(env, role_name)
    cmd = [
        'bash', '-c',
        'set -o pipefail; ' +  # We want to fail if mysqldump fails
        'mysqldump --add-drop-database --lock-all-tables '
        '--databases {0}'.format(' '.join(dbs)) +
        ' | gzip',
    ]
    with ssh.popen(cmd, stdout=ssh.PIPE, node=node) as proc:
        with open(fname, 'wb') as local_file:
            shutil.copyfileobj(proc.stdout, local_file)


def mysqldump_restore_to_env(env, role_name, fname):
    node = env_util.get_one_node_of(env, role_name)
    with open(fname, 'rb') as local_file:
        with ssh.popen(['sh', '-c', 'zcat | mysql'],
                       stdin=ssh.PIPE, node=node) as proc:
            shutil.copyfileobj(local_file, proc.stdin)


def db_sync(env):
    node = env_util.get_one_controller(env)
    ssh.call(['keystone-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(
        ['nova-manage', 'db', 'sync', '--version', '290'],
        node=node, parse_levels=True)
    ssh.call(
        ['nova-manage', 'db', 'migrate_flavor_data'],
        node=node, parse_levels=True)
    ssh.call(['nova-manage', 'db', 'sync'], node=node, parse_levels=True)
    ssh.call(['nova-manage', 'db', 'expand'], node=node, parse_levels=True)
    ssh.call(['nova-manage', 'db', 'migrate'], node=node, parse_levels=True)
    ssh.call(['heat-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(['glance-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(['neutron-db-manage', '--config-file=/etc/neutron/neutron.conf',
              'upgrade', 'head'], node=node, parse_levels='^(?P<level>[A-Z]+)')
    ssh.call(['cinder-manage', 'db', 'sync'], node=node, parse_levels=True)
