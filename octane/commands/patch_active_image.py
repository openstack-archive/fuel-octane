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

import hashlib
import os
import tarfile
import tempfile
import uuid
import yaml

from cliff import command
from oslo_log import log as logging

from octane import magic_consts
from octane.util import patch
from octane.util import subprocess
from octane.util import tempfile as temp_util


LOG = logging.getLogger(__name__)
IMAGE_LABEL = "patched_image"


def _patch_squashfs(root_img, patched_img, *patches):
    with temp_util.temp_dir() as patch_dir:
        LOG.info("unsquash root image to temporary directory")
        subprocess.call(["unsquashfs", "-f", "-d", patch_dir, root_img])
        LOG.info("apply patch to root image")
        patch.patch_apply(patch_dir, patches)
        LOG.info("create new root.squashfs image")
        subprocess.call(["mksquashfs", patch_dir, patched_img])


def calculate_md5(filename):
    md5 = hashlib.md5()
    chunk_size = 4048
    with open(filename, "rb") as f:
        block = f.read(chunk_size)
        while block:
            md5.update(block)
            block = f.read(chunk_size)
    return md5.hexdigest()


def _mk_metadata(src, dst, root_fs_path):
    with open(src) as fd:
        metadata = yaml.load(fd)

    uuid_val = metadata["uuid"]
    my_uuid_val = str(uuid.uuid1())
    metadata["label"] = IMAGE_LABEL
    metadata["uuid"] = my_uuid_val

    for module in metadata["modules"].values():
        module["uri"] = module["uri"].replace(uuid_val, my_uuid_val)

    metadata["modules"]["rootfs"]["raw_size"] = os.path.getsize(root_fs_path)
    metadata["modules"]["rootfs"]["raw_md5"] = calculate_md5(root_fs_path)
    with open(dst, "w") as fd:
        yaml.dump(metadata, fd)


def patch_img():
    root_img = os.path.join(magic_consts.ACTIVE_IMG_PATH, "root.squashfs")
    active_metadata_path = os.path.join(
        magic_consts.ACTIVE_IMG_PATH, "metadata.yaml")
    patch_file = os.path.join(magic_consts.CWD, "patches/fuel_agent/patch")
    path_archname_pairs = [(os.path.join(magic_consts.ACTIVE_IMG_PATH, p), p)
                           for p in ["vmlinuz", "initrd.img"]]

    with temp_util.temp_dir() as temp_dir:
        patched_img = os.path.join(temp_dir, "root.squashfs")
        patched_metadata_path = os.path.join(temp_dir, "metadata.yaml")

        _patch_squashfs(root_img, patched_img, patch_file)
        _mk_metadata(active_metadata_path, patched_metadata_path, patched_img)

        path_archname_pairs.append((patched_img, "root.squashfs"))
        path_archname_pairs.append((patched_metadata_path, "metadata.yaml"))

        with tempfile.NamedTemporaryFile() as archive_file:
            with tarfile.open(name=archive_file.name, mode="w:gz") as archive:
                for path, archname in path_archname_pairs:
                    archive.add(path, archname)

            LOG.info("Import image using fuel-bootstrap")
            subprocess.call(["fuel-bootstrap", "import", archive_file.name])
            LOG.info("Activate image using `fuel-bootstrap activate`")


class PatchImgCommand(command.Command):
    """Create patched bootstrap image with label `{0}`""".format(IMAGE_LABEL)

    def take_action(self, parsed_args):
        patch_img()
