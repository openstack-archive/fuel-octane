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
import os.path
import shutil
import time

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj

from octane import magic_consts
from octane.util import env as env_util
from octane.util import maintenance
from octane.util import ssh

LOG = logging.getLogger(__name__)


def get_databases(env):
    node = env_util.get_one_controller(env)
    with ssh.popen(
            ['mysql', '--batch', '--skip-column-names'],
            stdin=ssh.PIPE, stdout=ssh.PIPE, node=node) as proc:
        proc.stdin.write('SHOW DATABASES')
        out = proc.communicate()[0]
    return out.splitlines()


def mysqldump_from_env(env, dbs):
    existing_dbs = get_databases(env)
    dbs = set(existing_dbs) & set(dbs)
    LOG.info('Will dump tables: %s', ', '.join(dbs))

    node = env_util.get_one_controller(env)
    local_fname = os.path.join(magic_consts.FUEL_CACHE, 'dbs.original.sql.gz')
    cmd = [
        'bash', '-c',
        'set -o pipefail; ' +  # We want to fail if mysqldump fails
        'mysqldump --add-drop-database --lock-all-tables '
        '--databases {0}'.format(' '.join(dbs)) +
        ' | gzip',
    ]
    with ssh.popen(cmd, stdout=ssh.PIPE, node=node) as proc:
        with open(local_fname, 'wb') as local_file:
            shutil.copyfileobj(proc.stdout, local_file)
    local_fname2 = os.path.join(
        magic_consts.FUEL_CACHE,
        'dbs.original.cluster_%s.sql.gz' % (env.data['id'],),
    )
    shutil.copy(local_fname, local_fname2)
    return local_fname


def mysqldump_restore_to_env(env, fname):
    node = env_util.get_one_controller(env)
    with open(fname, 'rb') as local_file:
        with ssh.popen(['sh', '-c', 'zcat | mysql'],
                       stdin=ssh.PIPE, node=node) as proc:
            shutil.copyfileobj(local_file, proc.stdin)


def db_sync(env):
    node = env_util.get_one_controller(env)
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
    env_util.delete_fuel_resources(seed_env)
    # Wait for Neutron to reconfigure networks
    time.sleep(7)  # FIXME: Use more deterministic way
    maintenance.disable_apis(orig_env)
    maintenance.stop_corosync_services(seed_env)
    maintenance.stop_upstart_services(seed_env)
    fname = mysqldump_from_env(orig_env, magic_consts.OS_SERVICES)
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
