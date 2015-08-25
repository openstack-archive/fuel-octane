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

import glob
import os.path

from cliff import command as cmd

from octane import magic_consts
from octane.util import docker
from octane.util import subprocess


def patch_puppet():
    puppet_patch_dir = os.path.join(magic_consts.CWD, "patches", "puppet")
    for d in os.listdir(puppet_patch_dir):
        d = os.path.join(puppet_patch_dir, d)
        if not os.path.isdir(d):
            continue
        with open(os.path.join(d, "patch")) as patch:
            subprocess.call(["patch", "-Np3"], stdin=patch,
                            cwd=magic_consts.PUPPET_DIR)


def install_octane_nailgun():
    octane_nailgun = os.path.join(magic_consts.CWD, '..', 'octane_nailgun')
    subprocess.call(["python", "setup.py", "bdist_wheel"], cwd=octane_nailgun)
    wheel = glob.glob(os.path.join(octane_nailgun, 'dist', '*.whl'))[0]
    subprocess.call(["dockerctl", "copy", wheel, "nailgun:/root/"])
    docker.run_in_container("nailgun", ["pip", "install", "-U",
                                        "/root/" + os.path.basename(wheel)])
    docker.run_in_container("nailgun", ["pkill", "-f", "wsgi"])


def apply_patches(revert=False):
    for container, prefix, patch in magic_consts.PATCHES:
        docker.apply_patches(container, prefix,
                             os.path.join(magic_consts.CWD, patch),
                             revert=revert)


def prepare():
    if not os.path.isdir(magic_consts.FUEL_CACHE):
        os.makedirs(magic_consts.FUEL_CACHE)
    subprocess.call(["yum", "-y", "install"] + magic_consts.PACKAGES)
    subprocess.call(["pip", "install", "wheel"])
    patch_puppet()
    # From patch_all_containers
    apply_patches()
    install_octane_nailgun()


class PrepareCommand(cmd.Command):
    """Prepare the Fuel master node to upgrade an environment"""

    def take_action(self, parsed_args):
        prepare()


class RevertCommand(cmd.Command):
    """Revert all patches applied by 'prepare' command"""

    def take_action(self, parsed_args):
        apply_patches(revert=True)
