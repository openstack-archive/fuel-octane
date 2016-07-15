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

from octane import magic_consts
from octane.util import env as env_util
from octane.util import ssh


def get_databases(env):
    node = env_util.get_one_controller(env)
    with ssh.popen(
            ['mysql', '--batch', '--skip-column-names', '--host', 'localhost'],
            stdin=ssh.PIPE, stdout=ssh.PIPE, node=node) as proc:
        proc.stdin.write('SHOW DATABASES')
        out = proc.communicate()[0]
    return out.splitlines()


def mysqldump_from_env(env, dbs, fname):
    node = env_util.get_one_controller(env)
    cmd = [
        'bash', '-c',
        'set -o pipefail; ' +  # We want to fail if mysqldump fails
        'mysqldump --add-drop-database --lock-all-tables '
        '--host localhost '
        '--databases {0}'.format(' '.join(dbs)) +
        ' | gzip',
    ]
    with ssh.popen(cmd, stdout=ssh.PIPE, node=node) as proc:
        with open(fname, 'wb') as local_file:
            shutil.copyfileobj(proc.stdout, local_file)


def mysqldump_restore_to_env(env, fname):
    node = env_util.get_one_controller(env)
    with open(fname, 'rb') as local_file:
        with ssh.popen(['sh', '-c', 'zcat | mysql'],
                       stdin=ssh.PIPE, node=node) as proc:
            shutil.copyfileobj(local_file, proc.stdin)


def fix_neutron_migrations(node):
    sql_qs = [
        "insert into networksecuritybindings "
        "select id, 1 "
        "from networks "
        "where id not in (select network_id from networksecuritybindings);",
        "update ml2_network_segments "
        "set network_type='flat',physical_network='physnet1' "
        "where network_id in (select network_id from externalnetworks);",
    ]
    with ssh.popen(["mysql", "neutron"], node=node, stdin=ssh.PIPE) as proc:
        for sql in sql_qs:
            proc.stdin.write(sql);


def db_sync(env):
    node = env_util.get_one_controller(env)
    ssh.call(['keystone-manage', 'db_sync'], node=node, parse_levels=True)
    # migrate nova in few steps
    # at start sync up to 290 step
    # (this migration check flavor instances consistency)
    # than migrate flavor (transform them to normal state)
    # after that sync nova to the end
    with ssh.applied_patches(magic_consts.NOVA_PATCH_PREFIX_DIR,
                             node,
                             *magic_consts.NOVA_PATCHES):
        ssh.call(
            ['nova-manage', 'db', 'sync', '--version', '290'],
            node=node, parse_levels=True)
        ssh.call(
            ['nova-manage', 'db', 'migrate_flavor_data'],
            node=node, parse_levels=True)
        ssh.call(['nova-manage', 'db', 'sync'], node=node, parse_levels=True)
        ssh.call(['nova-manage', 'db', 'expand'], node=node, parse_levels=True)
        ssh.call(['nova-manage', 'db', 'migrate'],
                 node=node, parse_levels=True)
    ssh.call(['heat-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(['glance-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(['neutron-db-manage', '--config-file=/etc/neutron/neutron.conf',
              'upgrade', 'head'], node=node, parse_levels='^(?P<level>[A-Z]+)')
    fix_neutron_migrations(node)
    ssh.call(['cinder-manage', 'db', 'sync'], node=node, parse_levels=True)
