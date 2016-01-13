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


class PathArchivator(Base):
    PATH = None
    NAME = None

    def backup(self):
        assert self.PATH
        assert self.NAME
        self.archive.add(self.PATH, self.NAME)
