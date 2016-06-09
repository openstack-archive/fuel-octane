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
import tarfile
import uuid
import yaml

from octane import magic_consts
from octane.util import helpers
from octane.util import patch
from octane.util import subprocess


def _patch_squashfs(root_img, img_dir, *patches):
    patched_img = helpers.get_tempname(dir=img_dir)
    with helpers.temp_dir() as patch_dir:
        with helpers.temp_dir() as mount_dir:
            subprocess.call(
                ["mount", "-o", "loop", "-t", "squashfs", root_img, mount_dir])
            shutil.copytree(mount_dir, patch_dir, True)
            subprocess.call(["ummount", mount_dir])
        patch.patch_apply(patch_dir, patches)
        subprocess.call(["mksquashfs", patch_dir, patched_img])
    return patched_img


def patch_img():
    active_img_dir = "/var/www/nailgun/bootstraps/active_bootstrap/"
    root_img = os.path.join(active_img_dir, "root.squashfs")
    patch_file = os.path.join(magic_consts.CWD, "patches/fuel_agent/patch")
    with helpers.temp_dir() as temp_dir:
        patched_img = _patch_squashfs(root_img, temp_dir, patch_file)
        metadata_path = helpers.get_tempname(temp_dir)
        metadata = yaml.load(os.path.join(active_img_dir, "metadata.yaml"))
        metadata["label"] = "patched_image"
        metadata["uuid"] = "{0}".format(uuid.uuid1())
        yaml.dump(metadata, metadata_path)
        archive_name = os.path.join(temp_dir, "upload_bootstrap_img")
        with tarfile.open(name=archive_name, mode="w:gz") as archive:
            archive.add(patched_img, "root.squashfs")
            archive.add(
                os.path.join(active_img_dir, "initrd.img"), "initrd.img")
            archive.add(os.path.join(active_img_dir, "vmlinuz"), "vmlinuz")
            archive.add(metadata, "metadata.yaml")
        subprocess.call(["fuel-bootstrap", "import", archive_name])
