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

from cliff import command as cmd

from octane import magic_consts
from octane.util import archivate
from octane.util import docker
from octane.util import subprocess


def patch_puppet(revert=False):
    puppet_patch_dir = os.path.join(magic_consts.CWD, "patches", "puppet")
    for d in os.listdir(puppet_patch_dir):
        d = os.path.join(puppet_patch_dir, d)
        if not os.path.isdir(d):
            continue
        with open(os.path.join(d, "patch")) as patch:
            try:
                subprocess.call(["patch", "-R", "-p3"], stdin=patch,
                                cwd=magic_consts.PUPPET_DIR)
            except subprocess.CalledProcessError:
                if not revert:
                    pass
                else:
                    raise
            if not revert:
                patch.seek(0)
                subprocess.call(["patch", "-N", "-p3"], stdin=patch,
                                cwd=magic_consts.PUPPET_DIR)


def apply_patches(revert=False):
    for container, prefix, patch in magic_consts.PATCHES:
        docker.apply_patches(container, prefix,
                             os.path.join(magic_consts.CWD, patch),
                             revert=revert)


def revert_initramfs():
    backup = magic_consts.BOOTSTRAP_INITRAMFS + '.bkup'
    os.rename(backup, magic_consts.BOOTSTRAP_INITRAMFS)


def patch_initramfs():
    with archivate.update_cpio(magic_consts.BOOTSTRAP_INITRAMFS) as chroot:
        patch_fuel_agent(chroot)
    docker.run_in_container("cobbler", ["cobbler", "sync"])


def patch_fuel_agent(chroot):
    patch_dir = os.path.join(magic_consts.CWD, "patches", "fuel_agent")
    with open(os.path.join(patch_dir, "patch")) as patch:
        subprocess.call(["patch", "-N", "-p0"], stdin=patch, cwd=chroot)


def prepare():
    if not os.path.isdir(magic_consts.FUEL_CACHE):
        os.makedirs(magic_consts.FUEL_CACHE)
    subprocess.call(["yum", "-y", "install"] + magic_consts.PACKAGES)
    # From patch_all_containers
    apply_patches()
    docker.run_in_container("nailgun", ["pkill", "-f", "wsgi"])
    patch_initramfs()


def revert_prepare():
    apply_patches(revert=True)
    docker.run_in_container("nailgun", ["pkill", "-f", "wsgi"])
    revert_initramfs()


class PrepareCommand(cmd.Command):
    """Prepare the Fuel master node to upgrade an environment"""

    def take_action(self, parsed_args):
        prepare()


class RevertCommand(cmd.Command):
    """Revert all patches applied by 'prepare' command"""

    def take_action(self, parsed_args):
        revert_prepare()
