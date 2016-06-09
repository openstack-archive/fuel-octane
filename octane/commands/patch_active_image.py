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
import os
import tarfile
import uuid
import yaml

from cliff import command

from octane import magic_consts
from octane.util import patch
from octane.util import subprocess
from octane.util import tempfile_helpers


LOG = logging.getLogger(__name__)


def _patch_squashfs(root_img, img_dir, *patches):
    patched_img = os.path.join(img_dir, "root.squashfs")
    with tempfile_helpers.temp_dir() as patch_dir:
        LOG.info("unsquash root image to temporary directory")
        subprocess.call(["unsquashfs", "-f", "-d", patch_dir, root_img])
        LOG.info("apply patch to root image")
        patch.patch_apply(patch_dir, patches)
        LOG.info("create new root.squashfs image")
        subprocess.call(["mksquashfs", patch_dir, patched_img])
    return patched_img


def patch_img():
    root_img = os.path.join(magic_consts.ACTIVE_IMG_PATH, "root.squashfs")
    patch_file = os.path.join(magic_consts.CWD, "patches/fuel_agent/patch")
    with tempfile_helpers.temp_dir() as temp_dir:
        patched_img = _patch_squashfs(root_img, temp_dir, patch_file)
        # make new metadata file
        metadata_path = tempfile_helpers.get_tempname(temp_dir)
        active_metadata_path = os.path.join(
            magic_consts.ACTIVE_IMG_PATH, "metadata.yaml")
        with open(active_metadata_path) as fd:
            metadata = yaml.load(fd)
        metadata["label"] = "patched_image"
        uuid_val = "{0}".format(uuid.uuid1())
        metadata["uuid"] = uuid_val
        with open(metadata_path, "w") as new_metadata_file:
            yaml.dump(metadata, new_metadata_file)
        # archivate patched image
        archive_name = os.path.join(temp_dir, "upload_bootstrap_img")
        LOG.info("Generate archive to import using fuel-bootstrap")
        with tarfile.open(name=archive_name, mode="w:gz") as archive:
            archive.add(patched_img, "root.squashfs")
            archive.add(
                os.path.join(magic_consts.ACTIVE_IMG_PATH, "initrd.img"),
                "initrd.img")
            archive.add(
                os.path.join(magic_consts.ACTIVE_IMG_PATH, "vmlinuz"),
                "vmlinuz")
            archive.add(metadata_path, "metadata.yaml")
        LOG.info("Import image using fuel-bootstrap")
        # import patched image archive using fuel-bootstrap
        subprocess.call(["fuel-bootstrap", "import", archive_name])
        LOG.info("Activate image using "
                 "`fuel-bootstrap activate {0}`".format(uuid_val))


class PatchImgCommand(command.Command):

    def take_action(self, parsed_args):
        patch_img()
