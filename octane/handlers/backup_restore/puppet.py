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

import os
import shutil
import tempfile
import yaml

from octane.handlers.backup_restore import base
from octane.util import helpers
from octane.util import puppet


class PuppetArchivator(base.DirsArchivator):
    path = "/etc/puppet"
    tag = "puppet"


class PuppetApplyHost(base.Base):

    def backup(self):
        pass

    def restore(self):
        fd, tmp_file_name = tempfile.mkstemp(
            dir="/etc/fuel",
            prefix=".astute.yaml.octane")
        os.close(fd)
        shutil.copy("/etc/fuel/astute.yaml", tmp_file_name)
        try:
            data = helpers.get_astute_dict()
            data["FUEL_ACCESS"]["password"] = self.context.password
            with open("/etc/fuel/astute.yaml", "w") as current:
                yaml.safe_dump(data, current, default_flow_style=False)
            puppet.apply_host()
        finally:
            shutil.move(tmp_file_name, "/etc/fuel/astute.yaml")
