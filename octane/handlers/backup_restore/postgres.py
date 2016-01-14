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

import six

from octane.handlers.backup_restore import base
from octane.util import docker
from octane.util import subprocess


class PostgresArchivatorMeta(type):

    def __init__(cls, name, bases, attr):
        super(PostgresArchivatorMeta, cls).__init__(name, bases, attr)
        cls.container = "postgres"
        if cls.db is not None and cls.cmd is None:
            cls.cmd = ["sudo", "-u", "postgres", "pg_dump", "-C", cls.db]
        if cls.db is not None and cls.filename is None:
            cls.filename = "postgres/{0}.sql".format(cls.db)


@six.add_metaclass(PostgresArchivatorMeta)
class PostgresArchivator(base.CmdArchivator):
    db = None

    def post_restore_hook(self):
        pass

    def restore(self):
        dump = self.archive.extractfile(self.filename)
        subprocess.call([
            "systemctl", "stop", "docker-{0}.service".format(self.db)
        ])
        docker.stop_container(self.db)
        docker.run_in_container(
            "postgres",
            ["sudo", "-u", "postgres", "dropdb", "--if-exists", self.db],
        )
        with docker.in_container("postgres",
                                 ["sudo", "-u", "postgres", "psql"],
                                 stdin=subprocess.PIPE) as process:
            process.stdin.write(dump.read())
        subprocess.call([
            "systemctl", "start", "docker-{0}.service".format(self.db)
        ])
        docker.start_container(self.db)
        self.post_restore_hook()


class NailgunArchivator(PostgresArchivator):
    db = "nailgun"

    def post_restore_hook(self):
        docker.run_in_container("nailgun", ["nailgun_syncdb"])


class KeystoneArchivator(PostgresArchivator):
    db = "keystone"

    def post_restore_hook(self):
        docker.run_in_container("keystone", ["keystone-manage", "db_sync"])
