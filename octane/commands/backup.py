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
import sys
import tarfile

from cliff import command

from octane.handlers import backup_restore

LOG = logging.getLogger(__name__)


def backup_smth(path_to_backup, archivators):
    if path_to_backup:
        _, ext = os.path.splitext(path_to_backup)
        if ext in [".gz", ".bz2"]:
            ext = ext[1:]
        else:
            ext = ""
        tar_obj = tarfile.open(path_to_backup, "w|{0}".format(ext))
    else:
        tar_obj = tarfile.open(fileobj=sys.stdout, mode="w|")
    with contextlib.closing(tar_obj) as archive:
        for manager in archivators:
            manager(archive).backup()


def backup_admin_node(path_to_backup):
    backup_smth(path_to_backup, backup_restore.ARCHIVATORS)


def backup_repo(path_to_backup):
    backup_smth(path_to_backup, backup_restore.REPO_ARCHIVATORS)


class BaseBackupCommand(command.Command):

    def get_parser(self, *args, **kwargs):
        parser = super(BaseBackupCommand, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "--to",
            type=str,
            dest="path",
            help="Path to tarball file with the backup information.")
        return parser


class BackupCommand(BaseBackupCommand):

    def take_action(self, parsed_args):
        backup_admin_node(parsed_args.path)


class BackupRepoCommand(BaseBackupCommand):

    def take_action(self, parsed_args):
        backup_repo(parsed_args.path)
