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
from octane.util import docker


class CobblerArchivator(base.ContainerArchivator):
    backup_directory = "/var/lib/cobbler/config/systems.d/"
    banned_files = ["default.json"]
    container = "cobbler"
    backup_name = "cobbler"

    def restore(self):
        super(CobblerArchivator, self).restore()
        docker.stop_container("cobbler")
        docker.start_container("cobbler")
