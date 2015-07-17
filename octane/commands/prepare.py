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

from octane.util import docker
from octane.util import subprocess

PACKAGES = ["postgresql.x86_64", "pssh", "patch", "python-pip"]
PATCHES = [
    ("astute", "/usr/lib64/ruby/gems/2.1.0/gems/astute-6.1.0/lib/astute",
     "docker/astute/resources/deploy_actions.rb.patch"),
    ("cobbler", "/usr/lib/python2.6/site-packages/cobbler",
     "docker/cobbler/resources/pmanager.py.patch"),
    ("nailgun", "/usr/lib/python2.6/site-packages/nailgun/volumes",
     "docker/nailgun/resources/manager.py.patch"),
    ("nailgun", "/", "../octane_nailgun/tools/urls.py.patch"),
]
# TODO: use pkg_resources for patches
CWD = os.path.join(os.path.dirname(__file__), "..")  # FIXME


def patch_puppet():
    puppet_dir = "/etc/puppet/2014.2.2-6.1/modules"
    puppet_patch_dir = os.path.join(CWD, "patches", "puppet")
    for d in os.listdir(puppet_patch_dir):
        if not os.path.isdir(d):
            continue
        with open(os.path.join(puppet_patch_dir, d, "patch")) as patch:
            subprocess.call(["patch", "-Np3"], stdin=patch, cwd=puppet_dir)


def install_octane_nailgun():
    octane_nailgun = os.path.join(CWD, '..', 'octane_nailgun')
    subprocess.call(["python", "setup.py", "bdist_wheel"], cwd=octane_nailgun)
    wheel = glob.glob(os.path.join(octane_nailgun, 'dist', '*.whl'))[0]
    subprocess.call(["dockerctl", "copy", wheel, "nailgun:/root/"])
    docker.run_in_container("nailgun", ["pip", "install", "-U",
                                        "/root/" + os.path.basename(wheel)])
    docker.run_in_container("nailgun", ["pkill", "-f", "wsgi"])


def apply_patches(revert=False):
    for container, prefix, patch in PATCHES:
        docker.apply_patches(container, prefix, os.path.join(CWD, patch),
                             revert=revert)
    docker.run_in_container("astute", ["supervisorctl", "restart", "astute"])


def prepare():
    subprocess.call(["yum", "-y", "install"] + PACKAGES)
    subprocess.call(["pip", "install", "wheel"])
    octane_fuelclient = os.path.join(CWD, '..', 'octane_fuelclient')
    subprocess.call(["pip", "install", "-U", octane_fuelclient])
    patch_puppet()
    # From patch_all_containers
    apply_patches()
    install_octane_nailgun()


class PrepareCommand(cmd.Command):
    def take_action(self, parsed_args):
        prepare()


class RevertCommand(cmd.Command):
    def take_action(self, parsed_args):
        apply_patches(revert=True)
