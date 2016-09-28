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
import subprocess

from octane.handlers import upgrade
from octane.helpers import transformations
from octane import magic_consts
from octane.util import env as env_util
from octane.util import ssh

LOG = logging.getLogger(__name__)


class ControllerUpgrade(upgrade.UpgradeHandler):
    def __init__(self, node, env, isolated, live_migration):
        super(ControllerUpgrade, self).__init__(
            node, env, isolated, live_migration)
        self.service_tenant_id = None
        self.gateway = None

    def get_fw_admin_default_gw(self):
        networks = self.env.get_network_data()['networks']
        default_gw_admin = None
        gw_admin = None
        node_group_id = self.node.data['group_id']
        for network in networks:
            if network['name'] != 'fuelweb_admin':
                continue
            if node_group_id == network['group_id']:
                gw_admin = network.get('gateway')
            if network['group_id'] is None:
                default_gw_admin = network.get('gateway')
        return gw_admin or default_gw_admin

    def predeploy(self):
        default_info = env_util.get_node_default_facts(self.env)
        deployment_info = []
        gw_admin = self.get_fw_admin_default_gw()
        if self.isolated:
            facts = [info for info
                     in default_info if info['uid'] == str(self.node.id)]
            env_util.write_facts_to_dir(facts, self.node.data['cluster'])

        for info in default_info:
            if not ('primary-controller' in info['roles'] or
                    info['uid'] == str(self.node.id)):
                continue
            if self.isolated:
                transformations.remove_ports(info)
                if info['uid'] == str(self.node.id):
                    endpoints = info["network_scheme"]["endpoints"]
                    self.gateway = endpoints["br-ex"]["gateway"]
                transformations.reset_gw_admin(info, gw_admin)
            # From run_ping_checker
            info['run_ping_checker'] = False
            env_util.prepare_net_info(info)
            deployment_info.append(info)
        if deployment_info:
            self.env.upload_facts('deployment', deployment_info)

    def skip_tasks(self):
        return magic_consts.SKIP_CONTROLLER_TASKS

    def postdeploy(self):
        if self.isolated and self.gateway:
            # From restore_default_gateway
            LOG.info("Deleting default route at node %s",
                     self.node.id)
            try:
                ssh.call(['ip', 'route', 'delete', 'default'], node=self.node)
            except subprocess.CalledProcessError as exc:
                LOG.warn("Cannot delete default route at node %s: %s",
                         self.node.id, exc.args[0])
            LOG.info("Set default route at node %s: %s",
                     self.node.id, self.gateway)
            ssh.call(['ip', 'route', 'add', 'default', 'via', self.gateway],
                     node=self.node)


def get_admin_gateway(environment):
    for net in environment.get_network_data()['networks']:
        if net["name"] == "fuelweb_admin":
            return net["gateway"]
