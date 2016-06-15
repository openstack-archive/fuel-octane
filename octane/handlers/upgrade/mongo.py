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

from distutils import version
from octane import magic_consts

from octane.handlers import upgrade
from octane.util import disk
from octane.util import env as env_util
from octane.util import node as node_util
from octane.util import puppet

LOG = logging.getLogger(__name__)


class MongoUpgrade(upgrade.UpgradeHandler):
    def prepare(self):
        env = self.node.env

        if env_util.incompatible_provision_method(env):
            self.create_configdrive_partition()
            disk.update_node_partition_info(self.node.id)

        mongo_legacy_version = version.StrictVersion(
            magic_consts.MONGO_LEGACY_CONF_VERSION)
        fuel_version = version.StrictVersion(env.data['fuel_version'])
        if fuel_version <= mongo_legacy_version:
            puppet.patch_modules()

        self.preserve_partition()

    def postdeploy(self):
        env = self.node.env

        mongo_legacy_version = version.StrictVersion(
            magic_consts.MONGO_LEGACY_CONF_VERSION)
        fuel_version = version.StrictVersion(env.data['fuel_version'])
        if fuel_version <= mongo_legacy_version:
            puppet.patch_modules(revert=True)

    # TODO(ogelbukh): move this action to base handler and set a list of
    # partitions to preserve as an attribute of a role.
    def preserve_partition(self):
        partition = 'mongo'
        node_util.preserve_partition(self.node, partition)

    def create_configdrive_partition(self):
        disks = disk.get_node_disks(self.node)
        if not disks:
            raise Exception("No disks info was found "
                            "for node {0}".format(self.node["id"]))
        # it was agreed that 10MB is enough for config drive partition
        size = 10
        disk.create_partition(disks[0]['name'], size, self.node)
