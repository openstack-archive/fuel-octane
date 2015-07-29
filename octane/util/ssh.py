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

_CLIENTS = {}
_CLIENTS_LOCK = threading.Lock()


def _get_client(node):
    node_id = node.data['id']
    try:
        return _CLIENTS[node_id]
    except KeyError:
        with _CLIENTS_LOCK:
            try:
                return _CLIENTS[node_id]
            except KeyError:
                client = _new_client(node.data['ip'])
                _CLIENTS[node_id] = client
                return client


def _new_client(ip):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, key_filename=magic_consts.SSH_KEYS)
    return client


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
