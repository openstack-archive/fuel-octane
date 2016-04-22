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
import stat
import subprocess

from octane.handlers import upgrade
from octane.helpers import disk
from octane import magic_consts
from octane.util import env as env_util
from octane.util import node as node_util
from octane.util import plugin
from octane.util import ssh

LOG = logging.getLogger(__name__)


class ComputeUpgrade(upgrade.UpgradeHandler):
    def prepare(self):
        env = self.node.env
        if env_util.get_env_provision_method(env) != 'image':
            self.create_configdrive_partition()
            disk.update_node_partition_info(self.node.id)
        if node_util.is_live_migration_supported(self.node):
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
            ssh.call(
                ["sh", "-c", ". /root/openrc; "
                 "nova service-enable {0} nova-compute".format(
                     self.node.data['fqdn'])],
                node=controller,
            )
        except subprocess.CalledProcessError as exc:
            LOG.warn("Cannot start service 'nova-compute' on {0} "
                     "by reason: {1}. Try again".format(
                         self.node.data['fqdn'], exc))
            ssh.call(
                ["sh", "-c", ". /root/openrc; "
                 "nova service-enable {0} nova-compute".format(
                     self.node.data['fqdn'].split('.', 1)[0])],
                node=controller,
            )

        orig_version = self.orig_env.data["fuel_version"]
        if orig_version == "6.1":
            openstack_release = magic_consts.VERSIONS[orig_version]
            node_util.add_compute_upgrade_levels(self.node, openstack_release)

            ssh.call(["service", "nova-compute", "restart"], node=self.node)

    def evacuate_host(self):
        controller = env_util.get_one_controller(self.env)
        with ssh.tempdir(controller) as tempdir:
            local_path = os.path.join(
                magic_consts.CWD, 'bin', 'host_evacuation.sh')
            remote_path = os.path.join(tempdir, 'host_evacuation.sh')
            sftp = ssh.sftp(controller)
            sftp.put(local_path, remote_path)
            sftp.chmod(remote_path, stat.S_IRWXO)
            ssh.call(
                [remote_path, node_util.get_nova_node_handle(self.node)],
                node=controller,
            )

    # TODO(ogelbukh): move this action to base handler and set a list of
    # partitions to preserve as an attribute of a role.
    def preserve_partition(self):
        partition = 'vm'
        node_util.preserve_partition(self.node, partition)

    def shutoff_vms(self):
        password = env_util.get_admin_password(self.env)
        controller = env_util.get_one_controller(self.env)
        run_cmd = ". /root/openrc; nova --os-password {0} " \
            "list --host {1}".format(password, self.node.data["hostname"])
        run_cmd += "|awk -F\| \'$4~/ACTIVE/{print($2)}\'|xargs -I% nova stop %"
        ssh.call(["sh", "-c", run_cmd], stdout=ssh.PIPE, node=controller)

    def create_configdrive_partition(self):
        disks = disk.get_node_disks(self.node)
        if not disks:
            raise Exception("No disks info was found "
                            "for node {0}".format(self.node["id"]))
        # it was agreed that 10MB is enough for config drive partition
        size = 10
        disk.create_partition(disks[0]['name'], size, self.node)

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
