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
import os

from octane.handlers.backup_restore import base


LOG = logging.getLogger(__name__)


class NailgunPluginsArchivator(base.PathArchivator):
    path = "/var/www/nailgun/plugins"
    name = "nailgun_plugins"

    def backup(self):
        if os.path.exists(self.path):
            return super(NailgunPluginsArchivator, self).backup()
        LOG.warning(
            "Path {0} doesn't exists, nothing to backup".format(self.path))
