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


class CephOsdUpgrade(upgrade.UpgradeHandler):
    def preupgrade(self):
        ceph.check_cluster(self.node)

    def prepare(self):
        ceph.patch_mcollective(self.node)
        ceph.set_osd_noout(self.env)

    def postdeploy(self):
        ceph.unset_osd_noout(self.env)
