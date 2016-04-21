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
import re

from octane.util import archivate
from octane.util import docker
from octane.util import subprocess


class Base(object):

    def __init__(self, archive, context=None):
        self.archive = archive
        self.context = context

    @property
    def archivator_name(self):
        name = re.sub(
            '([A-Z]+)', r' \1', self.__class__.__name__
        ).lower().strip()
        for replacer in ["archivator", "backup"]:
            if name.endswith(replacer):
                name = name[:-len(replacer)].strip()
        return name

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
    backup_name = None

    def backup(self):
        assert self.container
        assert self.backup_name
        assert self.backup_directory
        stdout, _ = docker.run_in_container(
            self.container,
            ["find", self.backup_directory, "-type", "f"],
            stdout=subprocess.PIPE)
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
                "{0}/{1}".format(self.backup_name, filename)
            )

    def restore(self):
        assert self.container
        assert self.backup_name
        assert self.backup_directory
        for member in archivate.filter_members(
                self.archive, self.backup_name):
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


class CollectionArchivator(Base):

    archivators_classes = []

    def __init__(self, *args, **kwargs):
        super(CollectionArchivator, self).__init__(*args, **kwargs)
        self.archivators = [c(*args, **kwargs)
                            for c in self.archivators_classes]

    def backup(self):
        for archvator in self.archivators:
            archvator.backup()

    def restore(self):
        for archvator in self.archivators:
            archvator.restore()

    def pre_restore_check(self):
        for archvator in self.archivators:
            archvator.pre_restore_check()
