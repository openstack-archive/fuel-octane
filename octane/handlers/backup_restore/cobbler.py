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

from octane.handlers.backup_restore import base
from octane.util import cobbler
from octane.util import puppet
from octane.util import subprocess


class CobblerSystemArchivator(base.PathFilterArchivator):
    backup_directory = "/var/lib/cobbler/config/systems.d/"
    banned_files = ["default.json"]
    backup_name = "cobbler"


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
        # NOTE(akscram): Ubuntu systems created in the 7.0 release
        # use the 'bootstrap' profile that was removed since 9.0.
        with cobbler.rename_bootstrap_profile_for_systems():
            super(CobblerArchivator, self).restore()
            subprocess.call(["systemctl", "stop", "cobblerd"])
            puppet.apply_task("cobbler")
