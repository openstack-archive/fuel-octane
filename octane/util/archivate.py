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

import cStringIO
import os
import tarfile

from octane.util import docker
from octane.util import subprocess


def archive_dirs(archive, src_path, tag_name):
    """Archive all dirs from src path

    saved all dirs from src path to archive with
    name like {tag_name}/{dir_name}

    :param archive: tar archive for writing or appending
    :param src_path: path for backuping dir
    :param tag_name: start part name for current backup dir
    """
    if not os.path.exists(src_path):
        return
    for directory in os.listdir(src_path):
        dirpath = os.path.join(src_path, directory)
        if not os.path.isdir(dirpath):
            continue
        if os.path.islink(dirpath):
            continue
        archive.add(dirpath, "{0}/{1}".format(tag_name, directory))


def archivate_container_cmd_output(archive, container, cmd, filename):
    """archivate container command aoutput

    save command output runnning in container to archive with current tag
    :param archive: tar archive for writing or appending
    :param container: container name
    :param cmd: sequence of program arguments
    :param filename: name for saving output in archive
    """
    info = tarfile.TarInfo(filename)
    dump = cStringIO.StringIO()
    data, _ = docker.run_in_container(
        container,
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    info.size = len(data)
    dump.write(data)
    dump.seek(0)
    archive.addfile(info, dump)
