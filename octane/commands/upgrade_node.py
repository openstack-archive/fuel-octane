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
import os
import time

from octane.helpers import tasks as tasks_helpers
from octane.helpers import transformations
from octane import magic_consts
from octane.util import subprocess

from cliff import command as cmd
from fuelclient.objects import environment as environment_obj
from fuelclient.objects import node as node_obj

LOG = logging.getLogger(__name__)


class UpgradeHandler(object):
    def __init__(self, node, env, isolated):
        self.node = node
        self.env = env
        self.isolated = isolated

    def preupgrade(self):
        raise NotImplementedError('preupgrade')

    def prepare(self):
        raise NotImplementedError('prepare')

    def predeploy(self):
        raise NotImplementedError('predeploy')

    def postdeploy(self):
        raise NotImplementedError('postdeploy')


class ControllerUpgrade(UpgradeHandler):
    def predeploy(self):
        deployment_info = self.env.get_default_facts(
            'deployment', nodes=[self.node.data['id']])
        if self.isolated:
            # From backup_deployment_info
            self.env.write_facts_to_dir('deployment', deployment_info,
                                        directory=magic_consts.FUEL_CACHE)
            backup_path = os.path.join(
                magic_consts.FUEL_CACHE,
                "deployment_{0}".format(self.node.data['cluster']),
            )
            os.rename(backup_path, backup_path + '.orig')
        for info in deployment_info:
            if self.isolated:
                transformations.remove_physical_ports(info)
            # From run_ping_checker
            info['run_ping_checker'] = False
            transformations.remove_predefined_nets(info)
            transformations.reset_gw_admin(info)
        self.env.upload_facts('deployment', deployment_info)

        tasks = self.env.get_deployment_tasks()
        tasks_helpers.skip_tasks(tasks)
        self.env.update_deployment_tasks(tasks)

# TODO: use stevedore for this
role_upgrade_handlers = {
    'controller': ControllerUpgrade,
}


def get_role_upgrade_handlers(node, env, isolated):
    role_handlers = []
    for role in node.data['roles']:
        try:
            cls = role_upgrade_handlers[role]
        except KeyError:
            LOG.warn("Role '%s' is not supported, skipping")
        else:
            role_handlers.append(cls(node, env, isolated))
    return role_handlers


def call_role_upgrade_handlers(handlers, method):
    for node_handlers in handlers.values():
        for handler in node_handlers:
            try:
                getattr(handler, method)()
            except NotImplementedError:
                LOG.debug("Method '%s' not implemented in handler %s",
                          method, type(handler).__name__)


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


def upgrade_node(env_id, node_ids, isolated=False):
    # From check_deployment_status
    env = environment_obj.Environment(env_id)
    if env.data['status'] != 'new':
        raise Exception("Environment must be in 'new' status")
    nodes = [node_obj.Node(node_id) for node_id in node_ids]

    # Sanity check
    one_orig_id = None
    for node in nodes:
        orig_id = node.data['cluster']
        if orig_id == env_id:
            raise Exception(
                "Cannot upgrade node with ID %s: it's already in cluster with "
                "ID %s", node_id, env_id,
            )
        if orig_id:
            if one_orig_id and orig_id != one_orig_id:
                raise Exception(
                    "Not upgrading nodes from different clusters: %s and %s",
                    orig_id, one_orig_id,
                )
            one_orig_id = orig_id

    role_handlers = {}
    for node in nodes:
        role_handlers[node] = get_role_upgrade_handlers(node, env, isolated)

    call_role_upgrade_handlers(role_handlers, 'preupgrade')
    call_role_upgrade_handlers(role_handlers, 'prepare')

    subprocess.call(
        ["fuel2", "env", "move", "node", str(node_id), str(env_id)])
    for node in nodes:  # TODO: create wait_for_nodes method here
        wait_for_node(node, "discover")

    env.install_selected_nodes('provision', nodes)
    for node in nodes:  # TODO: create wait_for_nodes method here
        wait_for_node(node, "provisioned")

    call_role_upgrade_handlers(role_handlers, 'predeploy')

    env.install_selected_nodes('deploy', nodes)
    for node in nodes:  # TODO: create wait_for_nodes method here
        wait_for_node(node, "ready")

    call_role_upgrade_handlers(role_handlers, 'postdeploy')


class UpgradeNodeCommand(cmd.Command):
    """Move nodes to environment and upgrade the node"""

    def get_parser(self, prog_name):
        parser = super(UpgradeNodeCommand, self).get_parser(prog_name)
        parser.add_argument(
            '--isolated', action='store_true',
            help="Isolate node's network from original cluster")
        parser.add_argument(
            'env_id', type=int, metavar='ENV_ID',
            help="ID of target environment")
        parser.add_argument(
            'node_ids', type=int, metavar='NODE_ID', nargs='+',
            help="IDs of nodes to be moved")
        return parser

    def take_action(self, parsed_args):
        upgrade_node(parsed_args.env_id, parsed_args.node_ids,
                     isolated=parsed_args.isolated)
