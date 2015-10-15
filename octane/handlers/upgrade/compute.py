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

import os.path
import stat

from octane.handlers import upgrade
from octane.helpers import disk
from octane import magic_consts
from octane.util import env as env_util
from octane.util import node as node_util
from octane.util import plugin
from octane.util import ssh


class ComputeUpgrade(upgrade.UpgradeHandler):
    def prepare(self):
        env = self.node.env
        if env_util.get_env_provision_method(env) != 'image':
            self.create_configdrive_partition()
            disk.update_node_partition_info(self.node.id)
        self.backup_iscsi_initiator_info()
        self.preserve_partition()

    def postdeploy(self):
        self.restore_iscsi_initiator_info()
        controller = env_util.get_one_controller(self.env)
        ssh.call(
            ["sh", "-c", ". /root/openrc; "
             "nova service-enable {0} nova-compute".format(
                 self.node.data['fqdn'])],
            node=controller,
        )

        sftp = ssh.sftp(self.node)

        if self.orig_env.data["fuel_version"] == "6.1":
            with ssh.update_file(sftp, '/etc/nova/nova.conf') as (old, new):
                for line in old:
                    new.write(line)
                    if line.startswith("[upgrade_levels]"):
                        new.write("compute=juno\n")

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
                [remote_path, 'node-{0}'.format(self.node.data['id'])],
                node=controller,
            )

    # TODO(ogelbukh): move this action to base handler and set a list of
    # partitions to preserve as an attribute of a role.
    def preserve_partition(self):
        partition = 'vm'
        node_util.preserve_partition(self.node, partition)

    def shutoff_vms(self):
        password = env_util.get_admin_password(self.env)
        cmd = ['. /root/openrc;',
               'nova list --os-password {0} --host {1}'
               .format(password, self.node.data['hostname']),
               '|',
               'awk -F\| \'$4~/ACTIVE/{print($2)}',
               '|',
               'xargs -I% nova stop %']
        out, err = ssh.call(cmd, stdout=ssh.PIPE, node=self.node)

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
