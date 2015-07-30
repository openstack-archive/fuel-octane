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

import io
import logging
import pipes
import threading

import paramiko
from paramiko import channel

from octane import magic_consts
from octane.util import subprocess

LOG = logging.getLogger(__name__)


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
def _get_client(node):
    LOG.info("Creating new SSH connection to node %s", node.data['id'])
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(node.data['ip'], key_filename=magic_consts.SSH_KEYS)
    return client


@_get_client.check
def _check_client(node, client):
    t = client.get_transport()
    if t and t.is_active():
        return True
    LOG.info("SSH connection to node %s died, reconnecting", node.data['id'])
    return False


class ChannelFile(io.IOBase, channel.ChannelFile):
    pass


class ChannelStderrFile(io.IOBase, channel.ChannelStderrFile):
    pass


class _LogPipe(subprocess._BaseLogPipe):
    def __init__(self, level, pipe):
        super(_LogPipe, self).__init__(level)
        self._pipe = pipe

    def pipe(self):
        return self._pipe


class SSHPopen(subprocess.BasePopen):
    def __init__(self, name, cmd, popen_kwargs):
        self.node = popen_kwargs.pop('node')
        super(SSHPopen, self).__init__(name, cmd, popen_kwargs)
        self._channel = _get_client(self.node).get_transport().open_session()
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
        if 'stderr' not in self.popen_kwargs:
            self._pipe_stderr = _LogPipe(logging.ERROR, stderr)
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
