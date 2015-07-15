import contextlib
import os.path
import subprocess
import tarfile


def in_container(container, args, **popen_kwargs):
    """Create Popen object to run command defined by list args in container"""
    return subprocess.Popen(["dockerctl", "shell", container] + args,
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
    file."""
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
    with contextlib.closing(tar):
        for local_filename, docker_filename in find_files(source_dir):
            tar.add(local_filename, docker_filename)
    proc.wait()
    assert proc.returncode == 0  # Don't inline with proc.wait()!
    for local_filename, docker_filename in find_files(source_dir):
    for cur_dir, subdirs, files in os.walk(source_dir):
        if not compare_files(container, local_filename, docker_filename):
            raise Exception(
                "Contents of {0} differ from contents of {1} in container {2}"
                .format(local_filename, docker_filename, container)
            )
