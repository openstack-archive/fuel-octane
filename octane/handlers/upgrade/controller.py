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
import subprocess

import yaml

from octane.handlers import upgrade
from octane.helpers import tasks as tasks_helpers
from octane.helpers import transformations
from octane import magic_consts
from octane.util import env as env_util
from octane.util import node as node_util
from octane.util import plugin
from octane.util import ssh

LOG = logging.getLogger(__name__)


class ControllerUpgrade(upgrade.UpgradeHandler):
    def __init__(self, node, env, isolated):
        super(ControllerUpgrade, self).__init__(node, env, isolated)
        self.service_tenant_id = None
        self.gateway = None

    def preupgrade(self):
        self.service_tenant_id = env_util.cache_service_tenant_id(
            self.env, self.node)

    def predeploy(self):
        default_info = self.env.get_default_facts('deployment')
        deployment_info = env_util.get_deployment_info(self.env)
        network_data = self.env.get_network_data()
        gw_admin = transformations.get_network_gw(network_data,
                                                  "fuelweb_admin")
        if self.isolated:
            # From backup_deployment_info
            backup_path = os.path.join(
                magic_consts.FUEL_CACHE,
                "deployment_{0}.orig".format(self.node.data['cluster']),
            )
            if not os.path.exists(backup_path):
                os.makedirs(backup_path)
            # Roughly taken from Environment.write_facts_to_dir
            for info in default_info:
                if not info['uid'] == str(self.node.id):
                    continue
                fname = os.path.join(
                    backup_path,
                    "{0}_{1}.yaml".format(info['role'], info['uid']),
                )
                with open(fname, 'w') as f:
                    yaml.safe_dump(info, f, default_flow_style=False)
        for info in default_info:
            if not (info['role'] == 'primary-controller' or
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
            transformations.remove_predefined_nets(info)
            deployment_info.append(info)
        self.env.upload_facts('deployment', deployment_info)

        tasks = self.env.get_deployment_tasks()
        tasks_helpers.skip_tasks(tasks)
        self.env.update_deployment_tasks(tasks)

        if plugin.is_contrail_plugin_enabled(self.env):
            tasks = self.env.get_deployment_tasks()
            tasks_helpers.skip_tasks(tasks, tasks_helpers.SKIP_CONTRAIL_TASKS)
            self.env.update_deployment_tasks(tasks)

    def postdeploy(self):
        # From neutron_update_admin_tenant_id
        sftp = ssh.sftp(self.node)
        with ssh.update_file(sftp, '/etc/neutron/neutron.conf') as (old, new):
            for line in old:
                if line.startswith('nova_admin_tenant_id'):
                    new.write('nova_admin_tenant_id = {0}\n'.format(
                        self.service_tenant_id))
                else:
                    new.write(line)
        orig_version = self.orig_env.data["fuel_version"]
        if orig_version == "6.1":
            openstack_release = magic_consts.VERSIONS[orig_version]
            node_util.add_compute_upgrade_levels(self.node, openstack_release)

            nova_services = ssh.call_output(
                ["bash", "-c",
                 "initctl list | "
                 "awk '/nova/ && /start/ {print $1}' | tr '\n' ' '"],
                node=self.node
            )

            for nova_service in nova_services.split():
                ssh.call(["service", nova_service, "restart"], node=self.node)

        ssh.call(['restart', 'neutron-server'], node=self.node)
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
