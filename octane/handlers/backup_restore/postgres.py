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

from octane.handlers.backup_restore import base
from octane.util import docker
from octane.util import subprocess


class PostgresArchivator(base.CmdArchivator):
    CONTAINER = "postgres"
    CMD = ["sudo", "-u", "postgres", "pg_dumpall"]
    FILENAME = "postgres/dump.sql"

    def restore(self):
        dump = self.archive.extractfile(self.FILENAME)
        containers = ["keystone", "nailgun", "ostf"]
        for container in containers:
            subprocess.call([
                "systemctl", "stop", "docker-{0}.service".format(container)
            ])
            docker.run_in_container(
                "postgres",
                [
                    "sudo",
                    "-u",
                    "postgres",
                    "dropdb",
                    "--if-exists",
                    container,
                ])
        with subprocess.popen(
                [
                    "dockerctl",
                    "shell",
                    "postgres",
                    "sudo",
                    "-u",
                    "postgres",
                    "psql",
                ],
                stdin=subprocess.PIPE) as process:
            process.stdin.write(dump.read())
        for container in containers:
            subprocess.call([
                "systemctl", "start", "docker-{0}.service".format(container)
            ])
        docker.run_in_container("nailgun", ["nailgun_syncdb"])
        docker.run_in_container("keystone", ["keystone-manage", "db_sync"])
