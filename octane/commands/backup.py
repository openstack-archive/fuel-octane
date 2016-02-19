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
import tarfile

from cliff import command

from octane.handlers import backup_restore

LOG = logging.getLogger(__name__)


def backup(path_to_backup, archivators):
    ext = ""
    _, i_ext = os.path.splitext(path_to_backup)
    if i_ext in [".gz", ".bz2"]:
        ext = i_ext[1:]
    tar_obj = tarfile.open(path_to_backup, "w|{0}".format(ext))
    with contextlib.closing(tar_obj) as archive:
        for manager in archivators:
            manager(archive).backup()


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
