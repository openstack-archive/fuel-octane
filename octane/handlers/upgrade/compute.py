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
from octane import magic_consts
from octane.util import docker
from octane.util import env as env_util
from octane.util import node as node_util
from octane.util import ssh


class ComputeUpgrade(upgrade.UpgradeHandler):
    def prepare(self):
        self.update_partition_generator()
        self.preserve_partition()

    def postdeploy(self):
        controller = env_util.get_one_controller(self.env)
        ssh.call(
            ["sh", "-c", ". /root/openrc; "
             "nova service-enable node-{0} nova-compute".format(
                 self.node.data['id'])],
            node=controller,
        )

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

    def update_partition_generator(self):
        fname = 'update_release_partition_info.py'
        dest_folder = '/tmp'
        folder = os.path.join(magic_consts.CWD, 'patches')
        docker.put_files_to_docker('nailgun', dest_folder, folder)
        command = 'python {0}'.format(os.path.join(dest_folder, fname))
        docker.run_in_container('nailgun', [command])
