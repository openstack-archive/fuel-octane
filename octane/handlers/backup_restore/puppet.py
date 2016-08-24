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
from octane import magic_consts
from octane.util import auth
from octane.util import keystone
from octane.util import puppet
from octane.util import subprocess


class PuppetArchivator(base.DirsArchivator):
    path = "/etc/puppet"
    tag = "puppet"


class PuppetApplyTasks(base.Base):
    services = [
        "ostf",
    ]

    def backup(self):
        pass

    def restore(self):
        subprocess.call(["systemctl", "stop"] + self.services)
        with auth.set_astute_password(self.context), \
                keystone.admin_token_auth(magic_consts.KEYSTONE_PASTE,
                                          magic_consts.KEYSTONE_PIPELINES):
            puppet.apply_all_tasks()
