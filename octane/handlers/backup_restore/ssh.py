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


class SshArchivator(base.PathArchivator):
    path = "/root/.ssh/"
    name = "ssh"

    def restore(self):
        super(SshArchivator, self).restore()
        docker.run_in_container("cobbler",
                                ['cp', '/root/.ssh/authorized_keys',
                                 '/etc/cobbler/authorized_keys'])
