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

    with open(path_to_backup) as input_io:
        if not password:
            _restore(input_io, archivators)
        else:
            abs_path_to_backup = os.path.abspath(path_to_backup)
            prefix = ".{0}.".format(os.path.basename(path_to_backup))
            dirname = os.path.dirname(abs_path_to_backup)
            with tempfile.NamedTemporaryFile(
                    dir=dirname, prefix=prefix) as temp:
                with encryption.decrypt_io(password, input_io, temp):
                    pass
                temp.seek(0)
                _restore(temp, archivators)


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
        super(BaseRestoreCommand, self).take_action(parsed_args)
        assert self.archivators
        if not os.path.isfile(parsed_args.path):
            raise ValueError("Invalid path to backup file")
        restore(
            parsed_args.path,
            self.archivators,
            getattr(parsed_args, "password", None))


class RestoreCommand(BaseRestoreCommand, encryption.EncryptCommandMixin):

    archivators = backup_restore.ARCHIVATORS


class RestoreRepoCommand(BaseRestoreCommand):

    archivators = backup_restore.REPO_ARCHIVATORS
