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
from octane.util import encryption

LOG = logging.getLogger(__name__)


def backup(path_to_backup, archivators, password):
    _, ext = os.path.splitext(path_to_backup)
    if ext in [".gz", ".bz2"]:
        ext = ext[1:]
    else:
        ext = ""
    with tempfile.NamedTemporaryFile() as temp:
        tar_obj = tarfile.open(fileobj=temp, mode="w|{0}".format(ext))
        with contextlib.closing(tar_obj) as archive:
            for manager in archivators:
                manager(archive).backup()
            assert archive.getmembers(), "Nothing to backup"
        if password:
            with open(path_to_backup, "w") as backup_io:
                temp.seek(0)
                encryption.encrypt_io(temp, backup_io, password)
        else:
            temp.delete = False
            shutil.move(temp.name, path_to_backup)


class BaseBackupCommand(command.Command):

    archivators = None
    encrypted = False

    def get_parser(self, *args, **kwargs):
        parser = super(BaseBackupCommand, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "--to",
            type=str,
            dest="path",
            required=True,
            help="Path to tarball file with the backup information.")
        if self.encrypted:
            parser.add_argument(
                "--password",
                type=str,
                dest="password",
                help="")
            parser.add_argument(
                '--encrypted',
                dest='encrypted',
                action='store_true')
            parser.add_argument(
                '--not-encrypted',
                dest='encrypted',
                action='store_false')
            parser.set_defaults(encrypted=True)
        return parser

    def take_action(self, parsed_args):
        assert self.archivators
        password = None
        if self.encrypted:
            if parsed_args.encrypted != bool(parsed_args.password):
                raise AssertionError("Password required for encrypted backup")
            if parsed_args.encrypted:
                password = parsed_args.password
        backup(parsed_args.path, self.archivators, password)


class BackupCommand(BaseBackupCommand):

    archivators = backup_restore.ARCHIVATORS
    encrypted = True


class BackupRepoCommand(BaseBackupCommand):

    archivators = backup_restore.REPO_ARCHIVATORS
