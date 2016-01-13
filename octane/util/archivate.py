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
import subprocess
import tarfile
import tempfile


def archive_dirs(archive, src_path, tag_name):
    """Archive all dirs from src path

    saved all dirs from src path to archive with
    name like {tag_name}/{dir_name}

    :param: archive
    :param: src_path
    :param: tag_name
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


def extract_tag_to(archive, tag, dst_dir):
    """Extract all members from archive with current tag to destination dir

    :param: archive
    :param: tag
    :param: dst_dir
    """
    for member in archive:
        if not (member.name.startswith(tag) and member.isfile()):
            continue
        member.name = member.name.split("/", 1)[1]
        archive.extract(member, dst_dir)


def exec_cmd_in_container(container, cmd):
    """Exceute cmd in container and return result

    :param: container
    :param: cmd
    """
    data, _ = subprocess.call(
        ["dockerctl", "shell", container] + cmd.strip().split(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    return data


def archivate_container_cmd_output(archive, container, cmd, tag):
    """archivate container command aoutput

    save command output runnning in container to archive with current tag
    :param: archive
    :param: container
    :param: cmd
    :param: tag
    """
    info = tarfile.TarInfo(tag)
    dump = cStringIO.StringIO()
    data = exec_cmd_in_container(container, cmd)
    info.size = len(data)
    dump.write(data)
    dump.seek(0)
    archive.addfile(info, dump)


def restore_file_in_container(archive, container, tag, container_path):
    """restore file by tag name from archive

    restore file from archive get by tag to current path in conatiner

    :param: archive
    :param: container
    :param: tag
    :param: container_path
    """

    name, _ = subprocess.call([
        "docker",
        "ps",
        "--filter",
        "name={0}".format(container),
        '--format="{{.Names}}"'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE)
    name = name.strip()
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(archive.extractfile(tag).read())
    temp.close()
    subprocess.call([
        "docker", "cp", temp.name, "{0}:{1}".format(name, container_path)
    ])
    os.remove(temp.name)
