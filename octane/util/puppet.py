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

import os.path

from oslo_log import log as logging

from octane import magic_consts
from octane.util import patch
from octane.util import subprocess

LOG = logging.getLogger(__name__)


def apply_task(task):
    filename = '{0}.pp'.format(task)
    path = os.path.join(magic_consts.PUPPET_TASKS_DIR, filename)
    cmd = ['puppet', 'apply', '-d', '-v', "--color", "false",
           '--detailed-exitcodes', path]
    try:
        subprocess.call(cmd)
    except subprocess.CalledProcessError as exc:
        # NOTE(akscram): Detailed exit codes of puppet apply:
        # 0: The run succeeded with no changes or failures; the system
        #    was already in the desired state.
        # 1: The run failed, or wasn't attempted due to another run
        #    already in progress.
        # 2: The run succeeded, and some resources were changed.
        # 4: The run succeeded, and some resources failed.
        # 6: The run succeeded, and included both changes and failures.
        if exc.returncode != 2:
            LOG.error("Cannot apply the Puppet task: %s, %s",
                      task, exc.message)
            raise


def apply_all_tasks():
    try:
        subprocess.call([magic_consts.PUPPET_APPLY_TASKS_SCRIPT])
    except subprocess.CalledProcessError as exc:
        LOG.error("Cannot apply Puppet state on host: %s",
                  exc)
        raise


def patch_modules(revert=False):
    puppet_patch_dir = os.path.join(magic_consts.CWD, "patches", "puppet")
    patches = []
    for d in os.listdir(puppet_patch_dir):
        d = os.path.join(puppet_patch_dir, d)
        if not os.path.isdir(d):
            continue
        patches.append(os.path.join(d, "patch"))
    patch.patch_apply(magic_consts.PUPPET_DIR, patches, revert=revert)
