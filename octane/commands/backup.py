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

LOG = logging.getLogger(__name__)


def backup(path_to_backup, archivators):
    _, ext = os.path.splitext(path_to_backup)
    if ext in [".gz", ".bz2"]:
        ext = ext[1:]
    else:
        ext = ""
    abs_path_to_backup = os.path.abspath(path_to_backup)
    prefix = ".{0}.".format(os.path.basename(abs_path_to_backup))
    dirname = os.path.dirname(abs_path_to_backup)
    with tempfile.NamedTemporaryFile(dir=dirname, prefix=prefix) as temp:
        tar_obj = tarfile.open(fileobj=temp, mode="w|{0}".format(ext))
        with contextlib.closing(tar_obj) as archive:
            for manager in archivators:
                LOG.info("Start backup {0}".format(manager.archivator_name))
                manager(archive).backup()
                LOG.info("Finish backup {0}".format(manager.archivator_name))
            if not archive.getmembers():
                raise Exception("Nothing to backup")
        shutil.move(temp.name, abs_path_to_backup)
        temp.delete = False


class BaseBackupCommand(command.Command):

    archivators = None

    def get_parser(self, *args, **kwargs):
        parser = super(BaseBackupCommand, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "--to",
            type=str,
            dest="path",
            required=True,
            help="Path to tarball file with the backup information.")
        return parser

    def take_action(self, parsed_args):
        assert self.archivators
        backup(parsed_args.path, self.archivators)


class BackupCommand(BaseBackupCommand):

    archivators = backup_restore.ARCHIVATORS


class BackupRepoCommand(BaseBackupCommand):

    archivators = backup_restore.REPO_ARCHIVATORS
