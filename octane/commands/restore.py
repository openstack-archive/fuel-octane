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

import contextlib
import logging
import os
import shutil
import tarfile
import tempfile

from cliff import command

from octane.handlers import backup_restore
from octane import magic_consts
from octane.util import subprocess

LOG = logging.getLogger(__name__)


def restore_data(path_to_backup, archivators):
    with contextlib.closing(tarfile.open(path_to_backup)) as archive:
        archivators = [cls(archive) for cls in archivators]
        for archivator in archivators:
            archivator.pre_restore_check()
        for archivator in archivators:
            archivator.restore()


class BaseRestoreCommand(command.Command):

    archivators = None

    def get_parser(self, *args, **kwargs):
        parser = super(BaseRestoreCommand, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "--from",
            type=str,
            action="store",
            dest="path",
            required=True,
            help="path to backup file")
        return parser

    def take_action(self, parsed_args):
        assert self.archivators
        if not os.path.isfile(parsed_args.path):
            raise ValueError("Invalid path to backup file")
        restore_data(parsed_args.path, self.archivators)


class RestoreCommand(BaseRestoreCommand):

    archivators = backup_restore.ARCHIVATORS


class RestoreRepoCommand(BaseRestoreCommand):

    archivators = backup_restore.REPO_ARCHIVATORS


class UpdateBootstrapCentos(command.Command):

    def take_action(self, parsed_args):
        tmp_dir = tempfile.mkdtemp()
        try:
            with subprocess.popen(
                    ["gunzip", "-c", magic_consts.BOOTSTRAP_INITRAMFS],
                    stdout=subprocess.PIPE) as proc:
                subprocess.call(
                    ["cpio", "-id"], stdin=proc.stdout, cwd=tmp_dir)
            shutil.copy(
                "/root/.ssh/authorized_keys",
                os.path.join(tmp_dir, "root/.ssh/authorized_keys"))
            with tempfile.NamedTemporaryFile() as new_img:
                subprocess.call(
                    ["find | grep -v '^\.$' |cpio --format newc -o | gzip -c"],
                    shell=True,
                    stdout=new_img,
                    cwd=tmp_dir)
                shutil.move(new_img.name, magic_consts.BOOTSTRAP_INITRAMFS)
                new_img.delete = False
        finally:
            shutil.rmtree(tmp_dir)
