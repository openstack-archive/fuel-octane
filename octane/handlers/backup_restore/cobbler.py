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

import json
import os

from octane.handlers.backup_restore import base
from octane.util import archivate
from octane.util import helpers
from octane.util import puppet
from octane.util import subprocess


class CobblerSystemArchivator(base.PathFilterArchivator):
    backup_directory = "/var/lib/cobbler/config/systems.d/"
    banned_files = ["default.json"]
    backup_name = "cobbler"

    @staticmethod
    def get_default_profile():
        astute = helpers.load_yaml("/etc/astute/astuted.conf")
        profile = astute.get("bootstrap_profile", "ubuntu_bootstrap")
        return profile

    def restore(self):
        default_profile = self.get_default_profile()
        for member in archivate.filter_members(self.archive, self.backup_name):
            system = json.load(self.archive.extractfile(member))
            if system["profile"] == "bootstrap":
                system["profile"] = default_profile
            filename = os.path.basename(member.name)
            extract_path = os.path.join(self.backup_directory, filename)
            with open(extract_path, "wb") as fp:
                json.dump(system, fp)
            os.chmod(extract_path, member.mode)


class CobblerProfileArchivator(base.PathFilterArchivator):
    backup_directory = "/var/lib/cobbler/config/profiles.d/"
    banned_files = ["bootstrap.json", "ubuntu_bootstrap.json"]
    backup_name = "cobbler_profiles"


class CobblerDistroArchivator(base.PathFilterArchivator):
    backup_directory = "/var/lib/cobbler/config/distros.d/"
    banned_files = ["bootstrap.json", "ubuntu_bootstrap.json"]
    backup_name = "cobbler_distros"


class CobblerArchivator(base.CollectionArchivator):

    archivators_classes = [
        CobblerSystemArchivator,
        CobblerProfileArchivator,
        CobblerDistroArchivator,
    ]

    def restore(self):
        super(CobblerArchivator, self).restore()
        subprocess.call(["systemctl", "stop", "cobblerd"])
        puppet.apply_task("cobbler")
