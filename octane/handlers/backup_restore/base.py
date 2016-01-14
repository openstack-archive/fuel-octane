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

import os

import six

from octane.util import archivate
from octane.util import docker
from octane.util import subprocess


class Base(object):

    def __init__(self, archive):
        self.archive = archive

    def backup(self):
        raise NotImplemented


class ContainerArchivator(Base):

    BANNED_FILES = []
    BACKUP_DIRECTORY = None
    ALLOWED_FILES = None
    CONTAINER = None

    def backup(self):
        assert self.CONTAINER
        assert self.BACKUP_DIRECTORY
        with docker.in_container(
                self.CONTAINER,
                ["find", self.BACKUP_DIRECTORY, "-type", "f"],
                stdout=subprocess.PIPE) as proc:
            stdout, _ = proc.communicate()
        filenames = stdout.strip().split()
        for filename in filenames:
            filename = filename[len(self.BACKUP_DIRECTORY):].lstrip("\/")
            if filename in self.BANNED_FILES:
                continue
            if self.ALLOWED_FILES is not None \
                    and filename not in self.ALLOWED_FILES:
                continue
            path = os.path.join(self.BACKUP_DIRECTORY, filename)
            archivate.archivate_container_cmd_output(
                self.archive,
                self.CONTAINER,
                ["cat", path],
                "{0}/{1}".format(self.CONTAINER, filename)
            )

    def restore(self):
        assert self.CONTAINER
        assert self.BACKUP_DIRECTORY
        for member in self.archive:
            if not member.name.startswith(self.CONTAINER):
                continue
            if not member.isfile():
                continue
            dump = self.archive.extractfile(member.name).read()
            name = member.name.split("/", 1)[-1]
            docker.write_data_in_docker_file(
                self.CONTAINER,
                os.path.join(self.BACKUP_DIRECTORY, name),
                dump
            )


class CmdArchivator(Base):

    CONTAINER = None
    CMD = None
    FILENAME = None

    def backup(self):
        assert self.CMD
        assert self.CONTAINER
        assert self.FILENAME

        archivate.archivate_container_cmd_output(
            self.archive, self.CONTAINER, self.CMD, self.FILENAME)


class DirsArchivator(Base):
    PATH = None
    TAG = None

    def backup(self):
        assert self.PATH
        assert self.TAG
        archivate.archive_dirs(self.archive, self.PATH, self.TAG)

    def restore(self):
        assert self.PATH
        assert self.TAG
        for member in self.archive:
            if not (member.name.startswith(self.TAG) and member.isfile()):
                continue
            member.name = member.name.split("/", 1)[1]
            self.archive.extract(member, self.PATH)


class PathArchivator(Base):
    PATH = None
    NAME = None

    def backup(self):
        assert self.PATH
        assert self.NAME
        self.archive.add(self.PATH, self.NAME)

    def restore(self):
        assert self.PATH
        assert self.NAME
        for member in self.archive:
            if not (member.name.startswith(self.NAME) and member.isfile()):
                continue
            if os.path.isdir(self.PATH):
                member.name = member.name.rsplit("/", 1)[-1]
                path = self.PATH
            elif os.path.isfile(self.PATH):
                path, member.name = member.rsplit("/", 1)
            self.archive.extract(member, path)


class PostgresArchivatorMeta(type):

    def __init__(cls, name, bases, attr):
        super(PostgresArchivatorMeta, cls).__init__(name, bases, attr)
        cls.CONTAINER = "postgres"
        if cls.DB is not None and cls.CMD is None:
            cls.CMD = ["sudo", "-u", "postgres", "pg_dump", "-c", cls.DB]
        if cls.DB is not None and cls.FILENAME is None:
            cls.FILENAME = "postgres/{0}.sql".format(cls.DB)


@six.add_metaclass(PostgresArchivatorMeta)
class PostgresArchivator(CmdArchivator):
    DB = None

    def post_restore_hook(self):
        pass

    def restore(self):
        dump = self.archive.extractfile(self.FILENAME)
        subprocess.call([
            "systemctl", "stop", "docker-{0}.service".format(self.DB)
        ])
        docker.stop_container(self.DB)
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
        subprocess.call([
            "systemctl", "start", "docker-{0}.service".format(self.DB)
        ])
        docker.start_container(self.DB)
        self.post_restore_hook()
