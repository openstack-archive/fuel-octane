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
from octane.util import db
from octane.util import deployment as deploy
from octane.util import env as env_util
from octane.util import maintenance

LOG = logging.getLogger(__name__)


def upgrade_db(orig_id, seed_id, db_role_name):
    orig_env = environment_obj.Environment(orig_id)
    seed_env = environment_obj.Environment(seed_id)
    env_util.delete_fuel_resources(seed_env)
    # Wait for Neutron to reconfigure networks
    time.sleep(7)  # FIXME: Use more deterministic way
    maintenance.disable_apis(orig_env)
    maintenance.stop_corosync_services(seed_env)
    maintenance.stop_upstart_services(seed_env)

    expected_dbs = set(magic_consts.OS_SERVICES)
    existing_dbs = set(db.get_databases(orig_env))
    dbs = existing_dbs & expected_dbs
    if len(dbs) < len(magic_consts.OS_SERVICES):
        LOG.info('Skipping nonexistent tables: %s',
                 ', '.join(expected_dbs - existing_dbs))
    LOG.info('Will dump tables: %s', ', '.join(dbs))

    fname = os.path.join(magic_consts.FUEL_CACHE, 'dbs.original.sql.gz')
    db.mysqldump_from_env(orig_env, db_role_name, dbs, fname)

    fname2 = os.path.join(
        magic_consts.FUEL_CACHE,
        'dbs.original.cluster_%s.sql.gz' % (orig_env.data['id'],),
    )
    shutil.copy(fname, fname2)

    db.mysqldump_restore_to_env(seed_env, db_role_name, fname)
    db.db_sync(seed_env)


def upgrade_db_with_graph(orig_id, seed_id):
    """Upgrade db using deployment graphs."""
    # Upload all graphs
    deploy.upload_graphs(orig_id, seed_id)

    # If any failure try to rollback ONLY original environment.
    try:
        deploy.execute_graph_and_wait("upgrade-db-orig", orig_id)
        deploy.execute_graph_and_wait("upgrade-db-seed", seed_id)
    except Exception:
        cluster_graphs = deploy.get_cluster_graph_names(orig_id)
        if 'upgrade-db-orig-rollback' in cluster_graphs:
            LOG.info("Trying to rollback 'upgrade-db' on the "
                     "environment '%s'.", orig_id)
            deploy.graph_execute_and_wait("upgrade-db-orig-rollback", orig_id)
        raise


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

        excl_group = parser.add_mutually_exclusive_group()
        excl_group.add_argument(
            '--db_role_name', type=str, metavar='DB_ROLE_NAME',
            default="controller", help="Set not standard role name for DB "
                                       "(default controller).")
        excl_group.add_argument(
            '--with-graph', action='store_true',
            help="EXPERIMENTAL: Use Fuel deployment graphs"
                 " instead of python-based commands.")

        return parser

    def take_action(self, parsed_args):
        # Execute alternative approach if requested
        if parsed_args.with_graph:
            upgrade_db_with_graph(parsed_args.orig_id, parsed_args.seed_id)
        else:
            upgrade_db(parsed_args.orig_id, parsed_args.seed_id,
                       parsed_args.db_role_name)
