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
import datetime
import logging
import os
import tarfile

from cliff import command

from octane.handlers import backup_restore

LOG = logging.getLogger(__name__)


def backup_admin_node(path_to_backup_dir):
    now_str = datetime.datetime.now().strftime("%Y_%m_%H_%M_%S")
    backup_name = "backup_{0}.tar.gz".format(now_str)
    backup_path = os.path.join(path_to_backup_dir, backup_name)
    with contextlib.closing(tarfile.open(backup_path, "w:gz")) as archive:
        for manager in backup_restore.MANAGERS:
            manager(archive).backup()


class BackupCommand(command.Command):

    def get_parser(self, *args, **kwargs):
        parser = super(BackupCommand, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "--to",
            type=str,
            action="store",
            dest="path",
            required=True,
            help="path to backup dir")
        return parser

    def take_action(self, parsed_args):
        if not os.path.isdir(parsed_args.path):
            raise ValueError("Invalid path to cakup dir")
        backup_admin_node(parsed_args.path)
