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

from octane.handlers import install
from octane import magic_consts
from octane.util import disk 
from octane.util import node as node_util
from octane.util import plugin
from octane.util import ssh

LOG = logging.getLogger(__name__)


class ComputeInstall(install.InstallHandler):
    def prepare(self):
        self.create_configdrive_partition()
        disk.update_node_partition_info(self.node.id)
        self.preserve_partition()

    def postdeploy(self):
        self.restore_iscsi_initiator_info()

    # TODO(ogelbukh): move this action to base handler and set a list of
    # partitions to preserve as an attribute of a role.
    def preserve_partition(self):
        partition = 'vm'
        node_util.preserve_partition(self.node, partition)

    def create_configdrive_partition(self):
        disks = disk.get_node_disks(self.node)
        if not disks:
            raise Exception("No disks info was found "
                            "for node {0}".format(self.node["id"]))
        # it was agreed that 10MB is enough for config drive partition
        size = 10
        disk.create_partition(disks[0]['name'], size, self.node)

    def restore_iscsi_initiator_info(self):
        if not plugin.is_enabled(self.env, 'emc_vnx'):
            return
        bup_file_path = get_iscsi_bup_file_path(self.node)
        if not os.path.exists(bup_file_path):
            LOG.warn("Backup iscsi configuration is not present for "
                     "compute node %s" % str(self.node.id))
            return
        ssh.sftp(self.node).put(bup_file_path, magic_consts.ISCSI_CONFIG_PATH)
        for service in ["open-iscsi", "multipath-tools", "nova-compute"]:
            ssh.call(['service', service, 'restart'], node=self.node)


def get_iscsi_bup_file_path(node):
    base_bup_path = os.path.join(magic_consts.FUEL_CACHE,
                                 "iscsi_initiator_files")
    return os.path.join(base_bup_path, node.data['hostname'])
