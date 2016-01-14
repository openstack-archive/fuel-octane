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

from octane.util import archivate
from octane.util import docker
from octane.util import subprocess


class Base(object):

    def __init__(self, archive):
        self.archive = archive

    def backup(self):
        raise NotImplemented


class ContainerArchivator(Base):

    banned_files = []
    backup_directory = None
    allowed_files = None
    container = None

    def backup(self):
        assert self.container
        assert self.backup_directory
        with docker.in_container(
                self.container,
                ["find", self.backup_directory, "-type", "f"],
                stdout=subprocess.PIPE) as proc:
            stdout, _ = proc.communicate()
        filenames = stdout.strip().split()
        for filename in filenames:
            filename = filename[len(self.backup_directory):].lstrip("\/")
            if filename in self.banned_files:
                continue
            if self.allowed_files is not None \
                    and filename not in self.allowed_files:
                continue
            path = os.path.join(self.backup_directory, filename)
            archivate.archivate_container_cmd_output(
                self.archive,
                self.container,
                ["cat", path],
                "{0}/{1}".format(self.container, filename)
            )

    def restore(self):
        assert self.container
        assert self.backup_directory
        for member in self.archive:
            if not member.name.startswith(self.container):
                continue
            if not member.isfile():
                continue
            dump = self.archive.extractfile(member.name).read()
            name = member.name.split("/", 1)[-1]
            docker.write_data_in_docker_file(
                self.container,
                os.path.join(self.backup_directory, name),
                dump
            )


class CmdArchivator(Base):

    container = None
    cmd = None
    filename = None

    def backup(self):
        assert self.cmd
        assert self.container
        assert self.filename

        archivate.archivate_container_cmd_output(
            self.archive, self.container, self.cmd, self.filename)


class DirsArchivator(Base):
    path = None
    tag = None

    def backup(self):
        assert self.path
        assert self.tag
        archivate.archive_dirs(self.archive, self.path, self.tag)

    def restore(self):
        assert self.path
        assert self.tag
        for member in self.archive:
            if not (member.name.startswith(self.tag) and member.isfile()):
                continue
            member.name = member.name.split("/", 1)[1]
            self.archive.extract(member, self.path)


class PathArchivator(Base):
    path = None
    name = None

    def backup(self):
        assert self.path
        assert self.name
        self.archive.add(self.path, self.name)

    def restore(self):
        assert self.path
        assert self.name
        for member in self.archive:
            if not (member.name.startswith(self.name) and member.isfile()):
                continue
            full_path = os.path.join(self.path, member.name[len(self.name):])
            path, member.name = full_path.rsplit('/', 1)
            self.archive.extract(member, path)
