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
import time

from octane.helpers import tasks as tasks_helpers
from octane.helpers import transformations
from octane import magic_consts
from octane.util import ssh
from octane.util import subprocess

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj

LOG = logging.getLogger(__name__)


class ControllerUpgrade(object):
    @staticmethod
    def cleanup(orig_env, node, seed_env):
        ssh.call(
            ["stop", "ceph-mon", "id=node-%s" % (node.data['id'],)],
            node=node,
        )
        ssh.call(["/etc/init.d/ceph", "start", "mon"], node=node)


# TODO: use stevedore for this
role_upgrade_handlers = {
    'controller': ControllerUpgrade,
}


def get_role_upgrade_handlers(roles):
    role_handlers = []
    for role in roles:
        try:
            role_handlers.append(role_upgrade_handlers[role])
        except KeyError:
            LOG.warn("Role '%s' is not supported, skipping")
    return role_handlers


def call_role_upgrade_handlers(handlers, method, *args, **kwargs):
    for handler in handlers:
        try:
            meth = getattr(handler, method)
        except AttributeError:
            LOG.debug("No '%s' method in handler %s", method, handler.__name__)
        else:
            meth(*args, **kwargs)


def wait_for_node(node, status, timeout=60 * 60, check_freq=60):
    node_id = node.data['id']
    LOG.debug("Waiting for node %s to transition to status '%s'",
              node_id, status)
    started_at = time.time()  # TODO: use monotonic timer
    while True:
        data = node.get_fresh_data()
        if data['status'] == 'error':
            raise Exception("Node %s fell into error status" % (node_id,))
        if data['online'] and data['status'] == status:
            LOG.info("Node %s transitioned to status '%s'", node_id, status)
            return
        if time.time() - started_at >= timeout:
            raise Exception("Timeout waiting for node %s to transition to "
                            "status '%s'" % (node_id, status))
        time.sleep(check_freq)


def upgrade_node(seed_id, node_id, isolated=False):
    # From check_deployment_status
    seed_env = environment_obj.Environment(seed_id)
    if seed_env.data['status'] != 'new':
        raise Exception("Environment must be in 'new' status")
    node = node_obj.Node(node_id)
    orig_id = node.data['cluster']
    if not orig_id:
        raise Exception("Cannot upgrade unallocated node with ID %s", node_id)
    orig_env = environment_obj.Environment(orig_id)

    role_handlers = get_role_upgrade_handlers(node.data['roles'])
    call_role_upgrade_handlers(role_handlers, 'prepare',
                               orig_env, node, seed_env)

    subprocess.call(
        ["fuel2", "env", "move", "node", str(node_id), str(seed_id)])
    wait_for_node(node, "discover")

    call_role_upgrade_handlers(role_handlers, 'preprovision',
                               orig_env, node, seed_env)
    seed_env.install_selected_nodes('provision', [node])
    wait_for_node(node, "provisioned")

    deployment_info = seed_env.get_default_facts('deployment', nodes=[node_id])
    if isolated:
        # From backup_deployment_info
        seed_env.write_facts_to_dir('deployment', deployment_info,
                                    directory=magic_consts.FUEL_CACHE)
    for info in deployment_info:
        if isolated:
            transformations.remove_physical_ports(info)
        # From run_ping_checker
        info['run_ping_checker'] = False
        transformations.remove_predefined_nets(info)
        transformations.reset_gw_admin(info)
    seed_env.upload_facts('deployment', deployment_info)

    tasks = seed_env.get_deployment_tasks()
    tasks_helpers.skip_tasks(tasks)
    seed_env.update_deployment_tasks(tasks)

    seed_env.install_selected_nodes('deploy', [node])
    wait_for_node(node, "ready")

    call_role_upgrade_handlers(role_handlers, 'cleanup',
                               orig_env, node, seed_env)


def isolated_type(s):
    if s != 'isolated':
        raise ValueError(s)
    else:
        return True


class UpgradeNodeCommand(cmd.Command):
    def get_parser(self, prog_name):
        parser = super(UpgradeNodeCommand, self).get_parser(prog_name)
        parser.add_argument('seed_id', type=int, metavar='SEED_ID')
        parser.add_argument('node_id', type=int, metavar='NODE_ID')
        parser.add_argument('isolated', type=isolated_type, default=False,
                            nargs='?')
        return parser

    def take_action(self, parsed_args):
        upgrade_node(parsed_args.seed_id, parsed_args.node_id,
                     isolated=parsed_args.isolated)
