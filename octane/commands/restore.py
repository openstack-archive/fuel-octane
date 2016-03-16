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


def restore_data(path_to_backup, archivators, context):
    with contextlib.closing(tarfile.open(path_to_backup)) as archive:
        archivators = [cls(archive, context) for cls in archivators]
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
        restore_data(
            parsed_args.path,
            self.archivators,
            self.get_context(parsed_args))

    def get_context(self, parsed_args):
        return None


class RestoreCommand(BaseRestoreCommand):

    archivators = backup_restore.ARCHIVATORS

    def get_parser(self, *args, **kwargs):
        parser = super(RestoreCommand, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "--admin-password",
            type=str,
            action="store",
            dest="admin_password",
            required=True,
            help="Fuel admin password")
        return parser

    def get_context(self, parsed_args):
        return backup_restore.NailgunCredentialsContext(
            password=parsed_args.admin_password,
            user="admin"
        )


class RestoreRepoCommand(BaseRestoreCommand):

    archivators = backup_restore.REPO_ARCHIVATORS
