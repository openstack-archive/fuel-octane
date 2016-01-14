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

import contextlib
import io
import logging
import os.path
import shutil
import tarfile
import tempfile

from octane.util import subprocess

LOG = logging.getLogger(__name__)


def in_container(container, args, **popen_kwargs):
    """Create Popen object to run command defined by list args in container"""
    return subprocess.popen(["dockerctl", "shell", container] + args,
                            name=args[0],
                            **popen_kwargs)


def run_in_container(container, args, **popen_kwargs):
    """Run command defined by list args in container and fail if it fails"""
    return subprocess.call(
        ["dockerctl", "shell", container] + args,
        name=args[0],
        **popen_kwargs)


def compare_files(container, local_filename, docker_filename):
    """Check if file local_filename equals file docker_filename in container"""
    with open(local_filename, 'rb') as f:
        local_contents = f.read()
    with in_container(
            container, ["cat", docker_filename],
            stdout=subprocess.PIPE
            ) as proc:
        docker_contents, _ = proc.communicate()
    # TODO: compare by chunks
    return docker_contents == local_contents


def find_files(source_dir):
    """Recursively find all files in source_dir

    Returns tuple of full path and path relative to source_dir for each
    file.
    """
    for cur_dir, subdirs, files in os.walk(source_dir):
        assert cur_dir.startswith(source_dir)
        new_dir = cur_dir[len(source_dir) + 1:]
        for f in files:
            yield os.path.join(cur_dir, f), os.path.join(new_dir, f)


def put_files_to_docker(container, prefix, source_dir):
    """Put all files in source_dir to prefix dir in container"""
    source_dir = os.path.abspath(source_dir)
    for local_filename, docker_filename in find_files(source_dir):
        with open(local_filename) as data:
            write_data_in_docker_file(container, docker_filename, data.read())
    for local_filename, docker_filename in find_files(source_dir):
        docker_filename = os.path.join(prefix, docker_filename)
        if not compare_files(container, local_filename, docker_filename):
            raise Exception(
                "Contents of {0} differ from contents of {1} in container {2}"
                .format(local_filename, docker_filename, container)
            )


def write_data_in_docker_file(container, path, data):
    prefix, filename = path.rsplit("/", 1)
    info = tarfile.TarInfo(filename)
    info.size = len(data)
    run_in_container(container, ["mkdir", "-p", prefix])
    with in_container(
            container,
            ["tar", "-xv", "--overwrite", "-f", "-", "-C", prefix],
            stdin=subprocess.PIPE,
            ) as proc:
        tar = tarfile.open(fileobj=proc.stdin, mode='w|')
        with contextlib.closing(tar):
            dump = io.BytesIO(data)
            dump.seek(0)
            tar.addfile(info, dump)


def get_files_from_docker(container, files, destination_dir):
    """Get files in 'files' list from container to destination_dir"""
    with in_container(
            container,
            ["tar", "-cvf", "-"] + files,
            stdout=subprocess.PIPE,
            ) as proc:
        tar = tarfile.open(fileobj=proc.stdout, mode='r|')
        with contextlib.closing(tar):  # On 2.6 TarFile isn't context manager
            tar.extractall(destination_dir)


def get_files_from_patch(patch):
    """Get all files touched by a patch"""
    result = []
    with open(patch) as p:
        for line in p:
            if line.startswith('+++'):
                fname = line[4:].strip()
                if fname.startswith('b/'):
                    fname = fname[2:]
                tab_pos = fname.find('\t')
                if tab_pos > 0:
                    fname = fname[:tab_pos]
                result.append(fname)
    return result


def apply_patches(container, prefix, *patches, **kwargs):
    """Apply set of patches to a container's filesystem"""
    revert = kwargs.pop('revert', False)
    # TODO: review all logic here to apply all preprocessing steps to patches
    # beforehand
    tempdir = tempfile.mkdtemp(prefix='octane_docker_patches.')
    try:
        files = []
        for patch in patches:
            for fname in get_files_from_patch(patch):
                if fname.startswith(prefix):
                    files.append(fname[len(prefix) + 1:])
                else:
                    files.append(fname)
        files = [os.path.join(prefix, f) for f in files]
        get_files_from_docker(container, files, tempdir)
        prefix = os.path.dirname(files[0])  # FIXME: WTF?!
        direction = "-R" if revert else "-N"
        with subprocess.popen(
                ["patch", direction, "-p0", "-d", tempdir + "/" + prefix],
                stdin=subprocess.PIPE,
                ) as proc:
            for patch in patches:
                with open(patch) as p:
                    for line in p:
                        if line.startswith('+++'):  # FIXME: PLEASE!
                            try:
                                slash_pos = line.rindex('/', 4)
                                space_pos = line.index(' ', slash_pos)
                            except ValueError:
                                pass
                            else:
                                line = ('+++ ' +
                                        line[slash_pos + 1:space_pos] +
                                        '\n')
                        proc.stdin.write(line)
        put_files_to_docker(container, "/", tempdir)
    finally:
        shutil.rmtree(tempdir)


def get_docker_container_name(container, **extra_filtering):
    cmd = [
        "docker",
        "ps",
        "--filter",
        "name={0}".format(container),
        '--format="{{.Names}}"',
    ]

    for key, value in extra_filtering.iteritems():
        cmd.append("--filter")
        cmd.append("{0}={1}".format(key, value))

    return subprocess.call(cmd, stdout=subprocess.PIPE)[0].strip()


def stop_container(container):
    name = get_docker_container_name(container, status="running")
    if name:
        subprocess.call(["docker", "stop", name])
    LOG.warn("Nothing to stop, container not found")


def start_container(container):
    name = get_docker_container_name(container, status="exited")
    if name:
        subprocess.call(["docker", "start", name])
    LOG.warn("Nothing to start, container not found")
