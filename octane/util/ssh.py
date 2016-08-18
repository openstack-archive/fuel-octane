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
import os
import pipes
import random
import shutil
import threading

import paramiko
from paramiko import channel

from octane import magic_consts
from octane.util import subprocess

LOG = logging.getLogger(__name__)

PIPE = subprocess.PIPE


class _cache(object):
    def __init__(self, new):
        self.new = new
        self.cache = {}
        self.lock = threading.Lock()
        self.invalidate = []
        self.check_fn = None

    def __call__(self, node):
        node_id = node.data['id']
        try:
            obj = self.cache[node_id]
        except KeyError:
            obj = None
        else:
            if not self.check_fn or self.check_fn(node, obj):
                return obj
        # Now obj is either bad old obj or None
        with self.lock:
            try:
                new_obj = self.cache[node_id]
            except KeyError:
                pass  # Need to just create a new one
            else:
                if new_obj is not obj:
                    return new_obj  # Someone already created a new one
                # We're going to replace this obj, invalidate other caches
                for cache in self.invalidate:
                    with cache.lock:
                        cache.cache.pop(node_id, None)

            new_obj = self.new(node)
            self.cache[node_id] = new_obj
            return new_obj

    def check(self, fn):
        self.check_fn = fn
        return fn


@_cache
def get_client(node):
    LOG.info("Creating new SSH connection to node %s", node.data['id'])
    creds = get_env_credentials(node.env)

    params = {
        'username': creds['user'] if creds else 'root',
        'key_filename': magic_consts.SSH_KEYS,
    }

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(node.data['ip'], **params)
    return client


@get_client.check
def _check_client(node, client):
    t = client.get_transport()
    if t:
        # Send normal keepalive packet, but wait for result to let socket die
        t.global_request('keepalive@lag.net', wait=True)
        if t.is_active():
            return True
    LOG.info("SSH connection to node %s died, reconnecting", node.data['id'])
    return False


class ChannelFile(io.IOBase, channel.ChannelFile):
    pass


class ChannelStderrFile(io.IOBase, channel.ChannelStderrFile):
    pass


class _LogPipe(subprocess._BaseLogPipe):
    def __init__(self, level, pipe, parse_levels=False):
        super(_LogPipe, self).__init__(level, parse_levels=parse_levels)
        self._pipe = pipe

    def pipe(self):
        return self._pipe


class SSHPopen(subprocess.BasePopen):
    def __init__(self, name, cmd, popen_kwargs):
        self.node = popen_kwargs.pop('node')
        for key in ['stdin', 'stdout', 'stderr']:
            assert popen_kwargs.get(key) in [None, PIPE]
        super(SSHPopen, self).__init__(name, cmd, popen_kwargs)

        as_root = popen_kwargs.get('as_root', True)
        transport = get_client(self.node).get_transport()
        username = transport.get_username()

        if username != 'root' and as_root:
            cmd = ['sudo', '--'] + cmd

        self._channel = transport.open_session()
        self._channel.exec_command(" ".join(map(pipes.quote, cmd)))
        self.name = "%s[at node-%d]" % (self.name, self.node.data['id'])
        if 'stdin' not in self.popen_kwargs:
            self.close_stdin()
        else:
            self.stdin = ChannelFile(self._channel, 'wb')
        stdout = ChannelFile(self._channel, 'rb')
        if 'stdout' not in self.popen_kwargs:
            self._pipe_stdout = _LogPipe(logging.INFO, stdout)
            self._pipe_stdout.start(self.name + " stdout")
        else:
            self._pipe_stdout = None
            self.stdout = stdout
        stderr = ChannelStderrFile(self._channel, 'rb')

        stderr_level = self.popen_kwargs.pop('stderr_log_level', logging.ERROR)

        if 'stderr' not in self.popen_kwargs:
            self._pipe_stderr = _LogPipe(
                stderr_level, stderr,
                parse_levels=popen_kwargs.get('parse_levels', False),
            )
            self._pipe_stderr.start(self.name + " stderr")
        else:
            self._pipe_stderr = None
            self.stderr = stderr

    def poll(self):
        if self._channel.exit_status_ready():
            return self._channel.recv_exit_status()
        else:
            return None

    def wait(self):
        return self._channel.recv_exit_status()

    def terminate(self):
        self._channel.close()

    def close_stdin(self):
        self._channel.shutdown_write()

    def communicate(self):
        if self.stdin:
            self.close_stdin()
        if self.stdout:
            stdout = self.stdout.read()
        else:
            stdout = None
        if self.stderr:
            stderr = self.stderr.read()
        else:
            stderr = None
        return stdout, stderr


def popen(cmd, **kwargs):
    return subprocess.popen(cmd, popen_class=SSHPopen, **kwargs)


def call(cmd, **kwargs):
    return subprocess.call(cmd, popen_class=SSHPopen, **kwargs)


def call_output(cmd, **kwargs):
    return subprocess.call_output(cmd, popen_class=SSHPopen, **kwargs)


@_cache
def _get_sftp(node):
    transport = get_client(node).get_transport()
    username = transport.get_username()

    if username != 'root':
        LOG.info('Run sftp server as root on node %s', node.data['hostname'])
        channel = transport.open_channel('session')
        channel.exec_command('sudo ' + magic_consts.SFTP_SERVER_BIN)
        return paramiko.SFTPClient(channel)

    return paramiko.SFTPClient.from_transport(transport)

get_client.invalidate.append(_get_sftp)


def sftp(node):
    get_client(node)  # ensure we're still connected
    return _get_sftp(node)


@contextlib.contextmanager
def update_file(sftp, filename):
    old = sftp.open(filename, 'r')
    try:
        temp_filename = '%s.octane.%08x' % (filename,
                                            random.randrange(1 << 8 * 4))
        new = sftp.open(temp_filename, 'wx')
    except IOError:  # we're unlucky, try other name (or fail)
        temp_filename = '%s.octane.%08x' % (filename,
                                            random.randrange(1 << 8 * 4))
        new = sftp.open(temp_filename, 'wx')
    with contextlib.nested(old, new):
        try:
            yield old, new
        except subprocess.DontUpdateException:
            sftp.unlink(temp_filename)
            return
        except Exception:
            sftp.unlink(temp_filename)
            raise
        stat = old.stat()
        new.chmod(stat.st_mode)
        new.chown(stat.st_uid, stat.st_gid)

    bak_filename = filename + '.octane.bak'
    sftp.rename(filename, bak_filename)
    sftp.rename(temp_filename, filename)
    sftp.unlink(bak_filename)


@contextlib.contextmanager
def tempdir(node):
    out = call_output(['mktemp', '-d'], node=node)
    dirname = out[:-1]
    try:
        yield dirname
    finally:
        call(['rm', '-rf', dirname], node=node)


@contextlib.contextmanager
def applied_patches(cwd, node, *patches):
    patched_files = []
    try:
        for path in patches:
            with open(path, "rb") as patch:
                with popen(
                        ["patch", "-N", "-p1", "-d", cwd],
                        node=node, stdin=PIPE) as proc:
                    shutil.copyfileobj(patch, proc.stdin)
            patched_files.append(path)
        yield
    finally:
        patched_files.reverse()
        for path in patched_files:
            with open(path, "rb") as patch:
                with popen(
                        ["patch", "-R", "-p1", "-d", cwd],
                        node=node, stdin=PIPE) as proc:
                    shutil.copyfileobj(patch, proc.stdin)


def get_env_credentials(env):
    attrs = env.get_attributes()
    editable = attrs['editable'].get('service_user')

    if not editable:
        return None

    return {
        'user': editable['name']['value'],
        'password': editable['password']['value'],
    }


def remove_all_files_from_dirs(dir_names, node):
    for dir_name in dir_names:
        call(['rm', '-rf', os.path.join(dir_name, '*')], node=node)


def write_content_to_file(sftp, filename, content):
    with sftp.open(filename, 'w') as file:
        file.write(content)
