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
    env_with_set_noout = set()

    def preupgrade(self):
        ceph.check_cluster(self.node)

    def prepare(self):
        self.preserve_partition()
        # patch only on first prepare run
        if not self.env_with_set_noout:
            puppet.patch_modules()
        if self.env.data['id'] not in self.env_with_set_noout:
            self.env_with_set_noout.add(self.env.data['id'])
            ceph.set_osd_noout(self.env)

    def postdeploy(self):
        # revert only on first postdeploy run
        if self.env.data['id'] in self.env_with_set_noout:
            ceph.unset_osd_noout(self.env)
            self.env_with_set_noout.remove(self.env.data['id'])
        if not self.env_with_set_noout:
            puppet.patch_modules(revert=True)

    def preserve_partition(self):
        partition = 'ceph'
        node_util.preserve_partition(self.node, partition)
