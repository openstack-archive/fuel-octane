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

from octane.handlers import upgrade
from octane.util import ceph
from octane.util import node as node_util
from octane.util import puppet
from octane.util import subprocess

LOG = logging.getLogger(__name__)


class CephOsdUpgrade(upgrade.UpgradeHandler):

    def preupgrade(self):
        try:
            ceph.check_cluster(self.node)
        except subprocess.CalledProcessError as exc:
            LOG.warning(
                "Ceph cluster health is not OK, ignoring: {0}".format(exc))

    def prepare(self):
        self.preserve_partition()
        ceph.set_osd_noout(self.env)
        puppet.patch_modules()

    def postdeploy(self):
        ceph.unset_osd_noout(self.env)
        puppet.patch_modules(revert=True)

    def preserve_partition(self):
        partition = 'ceph'
        node_util.preserve_partition(self.node, partition)
