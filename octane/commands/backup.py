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
from octane.util import encryption

LOG = logging.getLogger(__name__)


def backup_admin_node(path_to_backup, password):
    if path_to_backup:
        _, ext = os.path.splitext(path_to_backup)
        if ext in [".gz", ".bz2"]:
            ext = ext[1:]
        else:
            ext = ""
    else:
        ext = ""
    r_fd, w_fd = os.pipe()
    write_fd = os.fdopen(w_fd, "w")
    read_fd = os.fdopen(r_fd)
    if os.fork():
        read_fd.close()
        tar_obj = tarfile.TarFile.open(
            fileobj=write_fd, mode="w|{0}".format(ext))
        with contextlib.closing(tar_obj) as archive:
            for manager in backup_restore.ARCHIVATORS:
                manager(archive).backup()
        os._exit()
    else:
        write_fd.close()
        if path_to_backup:
            with open(path_to_backup, "w") as output:
                encryption.encrypt_io(read_fd, output, password)
        else:
            encryption.encrypt_io(read_fd, sys.stdout, password)


class BackupCommand(command.Command):

    def get_parser(self, *args, **kwargs):
        parser = super(BackupCommand, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "--to",
            type=str,
            dest="path",
            help="Path to tarball file with the backup information.")
        parser.add_argument(
            "--password",
            type=str,
            dest="password",
            help="")
        return parser

    def take_action(self, parsed_args):
        backup_admin_node(parsed_args.path, parsed_args.password)
