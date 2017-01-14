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

import re
import shutil
import time

from distutils import version
from oslo_log import log as logging

from octane import magic_consts
from octane.util import env as env_util
from octane.util import node as node_util
from octane.util import ssh


LOG = logging.getLogger(__name__)


def get_databases(env):
    node = env_util.get_one_controller(env)
    with ssh.popen([
            'sudo', '-iu', 'root',
            'mysql',
            '--batch',
            '--skip-column-names',
            '--host', 'localhost',
    ], stdin=ssh.PIPE, stdout=ssh.PIPE, node=node) as proc:
        proc.stdin.write('SHOW DATABASES')
        out = proc.communicate()[0]
    return out.splitlines()


def does_perform_flavor_data_migration(env):
    env_version = version.StrictVersion(env.data["fuel_version"])
    return env_version == \
        version.StrictVersion(magic_consts.NOVA_FLAVOR_DATA_MIGRATION_VERSION)


def nova_migrate_flavor_data(env, attempts=20, attempt_delay=30):
    node = env_util.get_one_controller(env)
    for i in xrange(attempts):
        output = ssh.call_output(['nova-manage', 'db', 'migrate_flavor_data'],
                                 node=node, parse_levels=True)
        match = FLAVOR_STATUS_RE.match(output)
        if match is None:
            raise Exception(
                "The format of the migrate_flavor_data command was changed: "
                "'{0}'".format(output))
        params = match.groupdict()
        matched = int(params["matched"])
        completed = int(params["completed"])
        if matched == 0 or matched == completed:
            LOG.info("All flavors were successfully migrated.")
            return
        LOG.debug("Trying to migrate flavors data, iteration %s: %s matches, "
                  "%s completed.", i, matched, completed)
        time.sleep(attempt_delay)
    raise Exception(
        "After {0} attempts flavors data migration is still not completed."
        .format(attempts))

FLAVOR_STATUS_RE = re.compile(
    r"^(?P<matched>[0-9]+) instances matched query, "
    "(?P<completed>[0-9]+) completed$")


def does_perform_cinder_volume_update_host(env):
    env_version = version.StrictVersion(env.data["fuel_version"])
    return env_version == \
        version.StrictVersion(magic_consts.CINDER_UPDATE_VOLUME_HOST_VERSION)


def cinder_volume_update_host(orig_env, new_env):
    orig_controller = env_util.get_one_controller(orig_env)
    new_controller = env_util.get_one_controller(new_env)
    current_host = get_current_host(orig_controller)
    new_host = get_new_host(new_controller)
    ssh.call(["cinder-manage", "volume", "update_host",
              "--currenthost", current_host,
              "--newhost", new_host],
             node=new_controller, parse_levels=True)


def get_current_host(node):
    parameters = node_util.get_parameters(node, magic_consts.CINDER_CONF, {
        "host": [("DEFAULT", "host")],
        "backend": [("DEFAULT", "volume_backend_name")],
    })
    # NOTE(akscram): result = "rbd:volumes#DEFAULT"
    result = "{host}#{backend}".format(
        host=parameters["host"],
        backend=parameters["backend"],
    )
    return result


def get_new_host(node):
    parameters = node_util.get_parameters(node, magic_consts.CINDER_CONF, {
        "host": [("DEFAULT", "host"), ("RBD-backend", "backend_host")],
        "backend": [("RBD-backend", "volume_backend_name")],
    })
    # NOTE(akscram): result = "rbd:volumes@RBD-backend#RBD-backend"
    result = "{host}@{backend}#RBD-backend".format(
        host=parameters["host"],
        backend=parameters["backend"],
    )
    return result


def mysqldump_from_env(env, role_name, dbs, fname):
    node = env_util.get_one_node_of(env, role_name)
    cmd = [
        'bash', '-c',
        'set -o pipefail; ' +  # We want to fail if mysqldump fails
        'sudo -iu root '
        'mysqldump --add-drop-database --lock-all-tables '
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
        with ssh.popen(['sh', '-c', 'zcat | sudo -iu root mysql'],
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
    insert_physnet1 = \
        "INSERT INTO ml2_flat_allocations " \
        "SELECT b.* FROM (SELECT 'physnet1') AS b " \
        "WHERE NOT EXISTS (" \
        "SELECT 1 FROM ml2_flat_allocations " \
        "WHERE physical_network = 'physnet1'" \
        ");"
    cmd = ['sudo', '-iu', 'root', 'mysql', 'neutron']
    with ssh.popen(cmd, node=node, stdin=ssh.PIPE) as proc:
        proc.stdin.write(add_networksecuritybindings_sql)
        proc.stdin.write(insert_physnet1)
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
