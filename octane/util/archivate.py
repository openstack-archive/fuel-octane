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

from __future__ import absolute_import

import contextlib
import io
import itertools
import os
import shutil
import tarfile
import tempfile

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
    dump = io.BytesIO()
    data, _ = docker.run_in_container(container, cmd, stdout=subprocess.PIPE)
    info.size = len(data)
    dump.write(data)
    dump.seek(0)
    archive.addfile(info, dump)


def filter_members(archive, dir_name):
    if '/' not in dir_name:
        dir_name = "{0}/".format(dir_name)
    for member in archive:
        if member.isfile() and member.name.startswith(dir_name):
            yield member


@contextlib.contextmanager
def update_cpio(img_path, dir_path=None):
    tmp_dir = tempfile.mkdtemp(dir=dir_path)
    try:
        with subprocess.popen(
                ["gunzip", "-c", img_path],
                stdout=subprocess.PIPE) as proc:
            subprocess.call(
                ["cpio", "-id"], stdin=proc.stdout, cwd=tmp_dir)
        yield tmp_dir
        tmp_dir_len = len(tmp_dir)
        with tempfile.NamedTemporaryFile(dir=dir_path) as new_img:
            with subprocess.popen(
                    ["cpio", "--format", "newc", "-o"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    cwd=tmp_dir) as cpio:
                with subprocess.popen(
                        ["gzip", "-c"],
                        stdin=cpio.stdout,
                        stdout=new_img,
                        cwd=tmp_dir):
                    for path, dirs, files in os.walk(tmp_dir):
                        for name in itertools.chain(dirs, files):
                            p_name = os.path.join(path, name)[tmp_dir_len + 1:]
                            cpio.stdin.write("{0}\n".format(p_name))
                    cpio.stdin.close()
            shutil.move(new_img.name, img_path)
            new_img.delete = False
    finally:
        shutil.rmtree(tmp_dir)
