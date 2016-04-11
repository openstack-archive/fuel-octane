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

from octane.handlers import upgrade
from octane.util import ceph
from octane.util import node as node_util
from octane.util import puppet


class CephOsdUpgrade(upgrade.UpgradeHandler):
    __RUN_PREPARE = set()
    __RUN_POSTDEPLOY = set()

    def preupgrade(self):
        ceph.check_cluster(self.node)

    def prepare(self):
        self.preserve_partition()
        # patch only on first prepare run
        is_first_run = not self.__class__.__RUN_PREPARE
        if self.env.data['id'] not in self.__class__.__RUN_PREPARE:
            self.__class__.__RUN_PREPARE.add(self.env.data['id'])
            ceph.set_osd_noout(self.env)
        if is_first_run:
            puppet.patch_modules()
            self.__class__.__RUN_POSTDEPLOY = set()

    def postdeploy(self):
        # revert only on first postdeploy run
        is_first_run = not self.__class__.__RUN_POSTDEPLOY
        if self.env.data['id'] not in self.__class__.__RUN_POSTDEPLOY:
            self.__class__.__RUN_POSTDEPLOY.add(self.env.data['id'])
            ceph.unset_osd_noout(self.env)
        if is_first_run:
            puppet.patch_modules(revert=True)
            self.__class__.__RUN_PREPARE = set()

    def preserve_partition(self):
        partition = 'ceph'
        node_util.preserve_partition(self.node, partition)
