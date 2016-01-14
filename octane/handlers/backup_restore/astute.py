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
import yaml

from octane.handlers.backup_restore import base


class AstuteArchivator(base.PathArchivator):
    PATH = "/etc/fuel/astute.yaml"
    NAME = "astute/astute.yaml"

    def restore(self):
        dump = self.archive.extractfile(self.NAME)
        if not os.path.exists(self.PATH):
            raise Exception("no astute etc file")
        backup_yaml = yaml.load(dump)
        with open(self.PATH, "r") as current:
            current_yaml = yaml.load(current)
        new_yaml = backup_yaml.copy()
        new_yaml['BOOTSTRAP'] = current_yaml['BOOTSTRAP']
        with open(self.PATH, "w") as new:
            yaml.safe_dump(new_yaml, new, default_flow_style=False)
