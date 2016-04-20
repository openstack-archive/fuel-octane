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
import os.path

from octane import magic_consts
from octane.util import patch
from octane.util import subprocess

LOG = logging.getLogger(__name__)


def apply_all_tasks():
    path = os.path.join(magic_consts.PUPPET_DIR,
                        'fuel',
                        'examples',
                        'deploy.sh')
    subprocess.call([path])


def patch_modules(revert=False):
    puppet_patch_dir = os.path.join(magic_consts.CWD, "patches", "puppet")
    patches = []
    for d in os.listdir(puppet_patch_dir):
        d = os.path.join(puppet_patch_dir, d)
        if not os.path.isdir(d):
            continue
        patches.append(os.path.join(d, "patch"))
    patch.patch_apply(magic_consts.PUPPET_DIR, patches, revert=revert)
