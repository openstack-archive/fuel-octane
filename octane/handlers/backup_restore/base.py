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
import shutil
import tempfile

from octane.util import archivate
from octane.util import docker
from octane.util import subprocess


class Base(object):

    def __init__(self, archive):
        self.archive = archive

    def backup(self):
        raise NotImplemented

    def restore(self):
        raise NotImplemented

    def pre_restore_check(self):
        pass


class ContainerArchivator(Base):

    banned_files = []
    backup_directory = None
    allowed_files = None
    container = None

    def backup(self):
        assert self.container
        assert self.backup_directory
        stdout, _ = docker.run_in_container(
            self.container,
            ["find", self.backup_directory, "-type", "f"],
            stdout=subprocess.PIPE)
        filenames = stdout.strip().split()
        temp_dir = tempfile.mkdtemp()
        try:
            files = []
            for filename in filenames:
                filename = filename[len(self.backup_directory):].lstrip("\/")
                if filename in self.banned_files:
                    continue
                if self.allowed_files is not None \
                        and filename not in self.allowed_files:
                    continue
                files.append(os.path.join(self.backup_directory, filename))
            docker.get_files_from_docker(self.container, files, temp_dir)
            if self.backup_directory[0] == "/":
                back_dir = self.backup_directory[1:]
            else:
                back_dir = self.backup_directory
            self.archive.add(os.path.join(temp_dir, back_dir), self.container)
        finally:
            shutil.rmtree(temp_dir)

    def restore(self):
        assert self.container
        assert self.backup_directory
        temp_dir = tempfile.mkdtemp()
        try:
            for member in archivate.filter_members(
                    self.archive, self.container):
                member.name = member.name.split("/", 1)[-1]
                self.archive.extract(member, temp_dir)
            docker.put_files_to_docker(
                self.container, self.backup_directory, temp_dir)
        finally:
            shutil.rmtree(temp_dir)


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

        for member in archivate.filter_members(self.archive, self.tag):
            member.name = member.name.split("/", 1)[-1]
            self.archive.extract(member, self.path)


class PathArchivator(Base):
    path = None
    name = None

    def backup(self):
        assert self.path
        assert self.name
        self.archive.add(self.path, self.name)

    def pre_restore_check(self):
        members = list(archivate.filter_members(self.archive, self.name))
        if os.path.isfile(self.path) and len(members) > 1:
            raise Exception("try to restore in file more than 1 member")

    def restore(self):
        for member in archivate.filter_members(self.archive, self.name):
            if os.path.isfile(self.path):
                path, member.name = os.path.split(self.path)
            else:
                member.name = member.name.split("/", 1)[-1]
                path = self.path
            self.archive.extract(member, path)
