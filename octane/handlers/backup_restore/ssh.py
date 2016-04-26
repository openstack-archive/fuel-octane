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
from octane.util import fuel_bootstrap
from octane.util import subprocess


class SshArchivator(base.PathArchivator):
    path = "/root/.ssh/"
    name = "ssh"

    def restore(self):
        super(SshArchivator, self).restore()
        subprocess.call(
            ["fuel-bootstrap", "build", "--activate"],
            env=self.context.get_credentials_env())

        # Remove old images cause they were created with old ssh keys pair
        for image_uuid in fuel_bootstrap.get_not_active_images_uuids():
            if image_uuid not in magic_consts.BOOTSTRAP_UNSUPPORTED_IMAGES:
                fuel_bootstrap.delete_image(image_uuid)
