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
import tempfile

from cliff import command

from octane.handlers import backup_restore
from octane.util import encryption

LOG = logging.getLogger(__name__)


def _restore(io_arch, archivators):
    with contextlib.closing(tarfile.open(fileobj=io_arch)) as archive:
        archivators = [cls(archive) for cls in archivators]
        for archivator in archivators:
            archivator.pre_restore_check()
        for archivator in archivators:
            archivator.restore()


def restore(path_to_backup, archivators, password):
    if password:
        with contextlib.closing(tempfile.TemporaryFile()) as temp_file:
            with open(path_to_backup) as input_io:
                encryption.decrypt_io(input_io, temp_file, password)
            temp_file.seek(0)
            _restore(temp_file, archivators)
    else:
        with open(path_to_backup) as io_file:
            _restore(io_file, archivators)


class BaseRestoreCommand(command.Command):

    archivators = None
    encrypted = False

    def get_parser(self, *args, **kwargs):
        parser = super(BaseRestoreCommand, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "--from",
            type=str,
            action="store",
            dest="path",
            required=True,
            help="path to backup file")

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
        if not os.path.isfile(parsed_args.path):
            raise ValueError("Invalid path to backup file")
        restore(parsed_args.path, self.archivators, password)


class RestoreCommand(BaseRestoreCommand):

    archivators = backup_restore.ARCHIVATORS
    encrypted = True


class RestoreRepoCommand(BaseRestoreCommand):

    archivators = backup_restore.REPO_ARCHIVATORS
