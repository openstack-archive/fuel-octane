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
from octane.util import env as env_util
from octane.util import ssh


class ComputeUpgrade(upgrade.UpgradeHandler):
    def prepare(self):
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

    def postdeploy(self):
        controller = env_util.get_one_controller(self.env)
        ssh.call(
            ["sh", "-c", ". /root/openrc; "
             "nova service-enable node-{0} nova-compute".format(
                 self.node.data['id'])],
            node=controller,
        )
