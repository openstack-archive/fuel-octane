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
from octane.helpers import cluster

LOG = logging.getLogger(__name__)


def restore_admin_node(path_to_backup, password):
    with contextlib.closing(tarfile.open(path_to_backup)) as archive:
        for manager in backup_restore.MANAGERS:
            manager.restore(archive)
    post_restore_actions = {
        "client": cluster.NailgunClient(
            admin_node_ip="127.0.0.1",
            username="admin",
            password=password,
            tenant_name="admin",
        )
    }
    for action in backup_restore.POST_RESTORE_ACTIONS:
        action(**post_restore_actions)


class RestoreCommand(command.Command):

    def get_parser(self, *args, **kwargs):
        parser = super(RestoreCommand, self).get_parser(*args, **kwargs)
        parser.add_argument(
            "-p",
            "--path_to_backup",
            type=str,
            action="store",
            dest="path",
            required=True,
            help="path to backup dir")

        parser.add_argument(
            "-W",
            "--password",
            type=str,
            action="store",
            dest="password",
            required=True,
            help="Nailgun password")

        return parser

    def take_action(self, parsed_args):
        if not os.path.isfile(parsed_args.path):
            raise ValueError("Invalid path to backup file")
        restore_admin_node(parsed_args.path, parsed_args.password)
