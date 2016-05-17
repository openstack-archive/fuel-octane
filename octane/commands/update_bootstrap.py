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

from cliff import command

from octane import magic_consts
from octane.util import archivate


def update_centos_bootstrap():
    with archivate.update_cpio(magic_consts.BOOTSTRAP_INITRAMFS) as tmp_dir:
        shutil.copy2(
            "/root/.ssh/authorized_keys",
            os.path.join(tmp_dir, "root/.ssh/authorized_keys"))


class UpdateCentos(command.Command):
    """Update Centos bootstrap image"""

    def take_action(self, parsed_args):
        update_centos_bootstrap()
