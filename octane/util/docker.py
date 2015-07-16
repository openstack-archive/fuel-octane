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
import os.path
import shutil
import tarfile
import tempfile

from octane.util import subprocess


def in_container(container, args, **popen_kwargs):
    """Create Popen object to run command defined by list args in container"""
    return subprocess.popen(["dockerctl", "shell", container] + args,
                            name=args[0],
                            **popen_kwargs)


def run_in_container(container, args, **popen_kwargs):
    """Run command defined by list args in container and fail if it fails"""
    subprocess.call(["dockerctl", "shell", container] + args,
                    name=args[0],
                    **popen_kwargs)


def compare_files(container, local_filename, docker_filename):
    """Check if file local_filename equals file docker_filename in container"""
    with open(local_filename, 'rb') as f:
        local_contents = f.read()
    proc = in_container(container, ["cat", docker_filename],
                        stdout=subprocess.PIPE)
    docker_contents, _ = proc.communicate()
    assert proc.returncode == 0
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
    # TODO: watch after stdout/stderr here
    proc = in_container(
        container,
        ["tar", "-xv", "--overwrite", "-f", "-", "-C", prefix],
        stdin=subprocess.PIPE,
    )
    tar = tarfile.TarFile(fileobj=proc.stdin, mode='w')
    with contextlib.closing(tar):  # On 2.6 TarFile isn't context manager
        for local_filename, docker_filename in find_files(source_dir):
            tar.add(local_filename, docker_filename)
    proc.wait()
    assert proc.returncode == 0  # Don't inline with proc.wait()!
    for local_filename, docker_filename in find_files(source_dir):
        if not compare_files(container, local_filename, docker_filename):
            raise Exception(
                "Contents of {0} differ from contents of {1} in container {2}"
                .format(local_filename, docker_filename, container)
            )


def get_files_from_docker(container, files, destination_dir):
    """Get files in 'files' list from container to destination_dir"""
    # TODO: watch after stderr here
    proc = in_container(
        container,
        ["tar", "-cvf", "-"] + files,
        stdout=subprocess.PIPE,
    )
    tar = tarfile.TarFile(fileobj=proc.stdout, mode='r')
    with contextlib.closing(tar):  # On 2.6 TarFile isn't context manager
        tar.extractall(destination_dir)
    proc.wait()
    assert proc.returncode == 0


def get_files_from_patch(patch):
    """Get all files touched by a patch"""
    result = []
    with open(patch) as p:
        for line in p:
            if line.startswith('+++'):
                fname = line[4:].strip()
                if fname.startswith('b/'):
                    fname = fname[2:]
                result.append(fname)
    return result


def apply_patches(container, prefix, *patches):
    """Apply set of patches to a container's filesystem"""
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
        prefix = os.path.dirname(files[0])  # FIXME: WTF?!
        get_files_from_docker(container, files, tempdir)
        # TODO: watch after stdout/stderr here
        proc = subprocess.popen(
            ["patch", "-N", "-p0", "-d", tempdir + "/" + prefix],
            stdin=subprocess.PIPE,
        )
        for patch in patches:
            with open(patch) as p:
                for line in p:
                    if line.startswith('+++'):  # FIXME: PLEASE!
                        try:
                            slash_pos = line.index('/', start=4)
                            space_pos = line.index(' ', start=slash_pos)
                        except ValueError:
                            pass
                        else:
                            line = ('+++ ' + line[slash_pos + 1:space_pos] +
                                    '\n')
                    proc.stdin.write(line)
        put_files_to_docker(container, "/", tempdir)
    finally:
        os.removedirs(tempdir)
