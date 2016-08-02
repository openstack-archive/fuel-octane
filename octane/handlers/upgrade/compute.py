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
import subprocess
import time

from octane.handlers import upgrade
from octane import magic_consts
from octane.util import env as env_util
from octane.util import node as node_util
from octane.util import nova
from octane.util import plugin
from octane.util import ssh

LOG = logging.getLogger(__name__)


class TimeoutException(Exception):
    message = None

    def __init__(self, hostname, attempts):
        assert self.message
        super(TimeoutException, self).__init__(
            self.message.format(hostname=hostname, attempts=attempts))


class TimeoutHostEvacuationException(TimeoutException):
    message = "After {attempts} tries of live evacuation of {hostname} some " \
              "instances are not still migrated."


class TimeoutStopVMException(TimeoutException):
    message = "After {attempts} tries of stop vms of {hostname} some " \
              "instances are not still stopped."


class ComputeUpgrade(upgrade.UpgradeHandler):
    def prepare(self):
        if not self.live_migration:
            self.preserve_partition()
            self.shutoff_vms()
        elif node_util.is_live_migration_supported(self.node):
            self.evacuate_host()
        else:
            self.backup_iscsi_initiator_info()
            self.preserve_partition()

    def postdeploy(self):
        self.restore_iscsi_initiator_info()
        controller = env_util.get_one_controller(self.env)
        # FIXME: Add more correct handling of case
        # when node may have not full name in services data
        try:
            call_host = self.node.data['fqdn']
            nova.run_nova_cmd(
                ["nova", "service-enable", call_host, "nova-compute"],
                controller, False)
        except subprocess.CalledProcessError as exc:
            LOG.warn("Cannot start service 'nova-compute' on {0} "
                     "by reason: {1}. Try again".format(
                         self.node.data['fqdn'], exc))
            call_host = self.node.data['fqdn'].split('.', 1)[0]
            nova.run_nova_cmd(
                ["nova", "service-enable", call_host, "nova-compute"],
                controller, False)

        orig_version = self.orig_env.data["fuel_version"]
        openstack_release = magic_consts.VERSIONS[orig_version]
        node_util.add_compute_upgrade_levels(self.node, openstack_release)

        ssh.call(["service", "nova-compute", "restart"], node=self.node)

    @staticmethod
    def _get_compute_lists(controller):
        """return tuple of lists enabled and disabled computes"""
        compute_list_str = nova.run_nova_cmd([
            "nova", "service-list",
            "|", "awk", "'/nova-compute/ {print $6\"|\"$10}'"],
            controller,
            True)
        enabled_computes = []
        disabled_computes = []
        for line in compute_list_str.splitlines():
            fqdn, status = line.strip().split('|')
            if status == "enabled":
                enabled_computes.append(fqdn)
            elif status == "disabled":
                disabled_computes.append(fqdn)

        return (enabled_computes, disabled_computes)

    @staticmethod
    def _is_nova_instances_exists_in_state(controller, node_fqdn, state):
        result = nova.run_nova_cmd(['nova', 'list',
                                    '--host', node_fqdn,
                                    '--status', state,
                                    '--limit', '1',
                                    '--minimal'], controller).strip()
        return len(result.strip().splitlines()) != 4

    @classmethod
    def _waiting_for_state_completed(
            cls, controller, node_fqdn, state, exception_cls,
            attempts=180, attempt_delay=10):
        for iteration in xrange(attempts):
            LOG.info(
                "Waiting until migration ends on {0} "
                "hostname (iteration {1})".format(node_fqdn, iteration))
            if cls._is_nova_instances_exists_in_state(
                    controller, node_fqdn, state):
                time.sleep(attempt_delay)
            else:
                return
        raise exception_cls(node_fqdn, attempts)

    def evacuate_host(self):
        controller = env_util.get_one_controller(self.env)

        enabled_compute, disabled_computes = self._get_compute_lists(
            controller)

        if len(enabled_compute) < 2:
            raise Exception("You can't disable last enabled compute")

        node_fqdn = node_util.get_nova_node_handle(self.node)

        if node_fqdn in disabled_computes:
            LOG.warn("Node {0} already disabled".format(node_fqdn))
        else:
            nova.run_nova_cmd(
                ["nova", "service-disable", node_fqdn, "nova-compute"],
                controller, False)
        nova.run_nova_cmd(['nova', 'host-evacuate-live', node_fqdn],
                          controller, False)
        self._waiting_for_state_completed(
            controller, node_fqdn, "MIGRATING", TimeoutHostEvacuationException)

    # TODO(ogelbukh): move this action to base handler and set a list of
    # partitions to preserve as an attribute of a role.
    def preserve_partition(self):
        partition = 'vm'
        node_util.preserve_partition(self.node, partition)

    def shutoff_vms(self):
        password = env_util.get_admin_password(self.env)
        controller = env_util.get_one_controller(self.env)
        node_fqdn = node_util.get_nova_node_handle(self.node)
        instances_str = nova.run_nova_cmd([
            "nova", "--os-password", password, "list",
            "--host", node_fqdn, "--limit", "-1", "|",
            "awk -F\| '$4~/ACTIVE/{print($2)}'"], controller)
        instances = instances_str.strip().splitlines()
        for instance in instances:
            instance = instance.strip()
            nova.run_nova_cmd(
                ["nova", "stop", instance], controller, output=False)
        self._waiting_for_state_completed(
            controller, node_fqdn, "ACTIVE", TimeoutStopVMException)

    def backup_iscsi_initiator_info(self):
        if not plugin.is_enabled(self.env, 'emc_vnx'):
            return
        bup_file_path = get_iscsi_bup_file_path(self.node)
        file_dir = os.path.dirname(bup_file_path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        ssh.sftp(self.node).get(magic_consts.ISCSI_CONFIG_PATH, bup_file_path)

    def restore_iscsi_initiator_info(self):
        if not plugin.is_enabled(self.env, 'emc_vnx'):
            return
        bup_file_path = get_iscsi_bup_file_path(self.node)
        if not os.path.exists(bup_file_path):
            raise Exception("Backup iscsi configuration is not present for "
                            "compute node %s" % str(self.node.id))
        ssh.sftp(self.node).put(bup_file_path, magic_consts.ISCSI_CONFIG_PATH)
        for service in ["open-iscsi", "multipath-tools", "nova-compute"]:
            ssh.call(['service', service, 'restart'], node=self.node)


def get_iscsi_bup_file_path(node):
    base_bup_path = os.path.join(magic_consts.FUEL_CACHE,
                                 "iscsi_initiator_files")
    return os.path.join(base_bup_path, node.data['hostname'])
