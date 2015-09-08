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
import shutil
import tempfile

from cliff import command as cmd

from octane import magic_consts
from octane.util import docker
from octane.util import subprocess


def patch_puppet(revert=False):
    direction = "-R" if revert else "-N"
    puppet_patch_dir = os.path.join(magic_consts.CWD, "patches", "puppet")
    for d in os.listdir(puppet_patch_dir):
        d = os.path.join(puppet_patch_dir, d)
        if not os.path.isdir(d):
            continue
        with open(os.path.join(d, "patch")) as patch:
            subprocess.call(["patch", direction, "-p3"], stdin=patch,
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
    backup = magic_consts.BOOTSTRAP_INITRAMFS + '.bkup'
    chroot = tempfile.mkdtemp()
    try:
        os.rename(magic_consts.BOOTSTRAP_INITRAMFS, backup)
        subprocess.call("gunzip -c {0} | cpio -id".format(backup),
                        shell=True, cwd=chroot)
        patch_fuel_agent(chroot)
        with open(magic_consts.BOOTSTRAP_INITRAMFS, "wb") as f:
            subprocess.call("find | grep -v '^\.$' | cpio --format newc -o"
                            " | gzip -c", shell=True, stdout=f, cwd=chroot)
    finally:
        shutil.rmtree(chroot)


def patch_fuel_agent(chroot):
    patch_dir = os.path.join(magic_consts.CWD, "patches", "fuel_agent")
    with open(os.path.join(patch_dir, "patch")) as patch:
        subprocess.call(["patch", "-N", "-p0"], stdin=patch, cwd=chroot)


def prepare():
    if not os.path.isdir(magic_consts.FUEL_CACHE):
        os.makedirs(magic_consts.FUEL_CACHE)
    subprocess.call(["yum", "-y", "install"] + magic_consts.PACKAGES)
    subprocess.call(["pip", "install", "wheel"])
    # From patch_all_containers
    apply_patches()
    patch_initramfs()


def revert_prepare():
    apply_patches(revert=True)
    revert_initramfs()


class PrepareCommand(cmd.Command):
    """Prepare the Fuel master node to upgrade an environment"""

    def take_action(self, parsed_args):
        prepare()


class RevertCommand(cmd.Command):
    """Revert all patches applied by 'prepare' command"""

    def take_action(self, parsed_args):
        revert_prepare()
