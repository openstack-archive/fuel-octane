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
import re
import shutil
import time

from octane.util import env as env_util
from octane.util import ssh


LOG = logging.getLogger(__name__)


def get_databases(env):
    node = env_util.get_one_controller(env)
    with ssh.popen([
            'mysql',
            '--user', 'root',
            '--batch',
            '--skip-column-names',
            '--host', 'localhost',
    ], stdin=ssh.PIPE, stdout=ssh.PIPE, node=node) as proc:
        proc.stdin.write('SHOW DATABASES')
        out = proc.communicate()[0]
    return out.splitlines()


def nova_migrate_flavor_data(env, attempts=20, attempt_delay=30):
    node = env_util.get_one_controller(env)
    for i in xrange(attempts):
        output = ssh.call_output(['nova-manage', 'db', 'migrate_flavor_data'],
                                 node=node, parse_levels=True)
        match = FLAVOR_STATUS_RE.match(output)
        if not match:
            raise Exception(
                "The format of the migrate_flavor_data command was changed: "
                "'{0}'".format(output))
        params = match.groupdict()
        matched = int(params["matched"])
        completed = int(params["completed"])
        if matched == 0:
            LOG.info("All flavors were successfully migrated.")
            return
        LOG.debug("Trying to migrate flavors data, iteration %s: %s matches, "
                  "%s completed", i, matched, completed)
        time.sleep(attempt_delay)
    raise Exception(
        "After %s attempts flavors data migration is still not ""completed")

FLAVOR_STATUS_RE = re.compile(
    r"^(?P<matched>[0-9]+) instances matched query, "
    "(?P<completed>[0-9]+) completed$")


def mysqldump_from_env(env, role_name, dbs, fname):
    node = env_util.get_one_node_of(env, role_name)
    cmd = [
        'bash', '-c',
        'set -o pipefail; ' +  # We want to fail if mysqldump fails
        'mysqldump --add-drop-database --lock-all-tables '
        '--user root '
        '--host localhost '
        '--databases {0}'.format(' '.join(dbs)) +
        ' | gzip',
    ]
    with ssh.popen(cmd, stdout=ssh.PIPE, node=node) as proc:
        with open(fname, 'wb') as local_file:
            shutil.copyfileobj(proc.stdout, local_file)


def mysqldump_restore_to_env(env, role_name, fname):
    node = env_util.get_one_node_of(env, role_name)
    with open(fname, 'rb') as local_file:
        with ssh.popen(['sh', '-c', 'zcat | sudo -iu root mysql --user root'],
                       stdin=ssh.PIPE, node=node) as proc:
            shutil.copyfileobj(local_file, proc.stdin)


def fix_neutron_migrations(node):
    add_networksecuritybindings_sql = \
        "INSERT INTO networksecuritybindings " \
        "SELECT id, 1 " \
        "FROM networks " \
        "WHERE id NOT IN (SELECT network_id FROM networksecuritybindings);"
    update_network_segments_sql = \
        "UPDATE ml2_network_segments " \
        "SET network_type='flat',physical_network='physnet1' " \
        "WHERE network_id IN (SELECT network_id FROM externalnetworks);"

    cmd = ['sudo', '-iu', 'mysql', '--user', 'root', 'neutron']
    with ssh.popen(cmd, node=node, stdin=ssh.PIPE) as proc:
        proc.stdin.write(add_networksecuritybindings_sql)
        proc.stdin.write(update_network_segments_sql)


def db_sync(env):
    node = env_util.get_one_controller(env)
    ssh.call(['keystone-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(['nova-manage', 'db', 'sync'], node=node, parse_levels=True)
    ssh.call(['nova-manage', 'api_db', 'sync'], node=node, parse_levels=True)
    ssh.call(['heat-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(['glance-manage', 'db_sync'], node=node, parse_levels=True)
    ssh.call(['neutron-db-manage', '--config-file=/etc/neutron/neutron.conf',
              'upgrade', 'head'], node=node, parse_levels='^(?P<level>[A-Z]+)')
    fix_neutron_migrations(node)
    ssh.call(['cinder-manage', 'db', 'sync'], node=node, parse_levels=True)
