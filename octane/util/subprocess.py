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
import functools
import io
import logging
import os
import pipes
import subprocess
import threading

LOG = logging.getLogger(__name__)
PIPE = subprocess.PIPE


def _close_stdin(chain_fn=None):
    os.close(0)
    if chain_fn:
        chain_fn()


class _BaseLogPipe(threading.Thread):
    def __init__(self, level):
        super(_BaseLogPipe, self).__init__()
        self.log_name = None
        self.log_level = level

    def start(self, name):
        self.log_name = name
        super(_BaseLogPipe, self).start()

    def run(self):
        try:
            with self.pipe() as pipe:
                for line in pipe:
                    if line.endswith('\n'):
                        line = line[:-1]
                    LOG.log(self.log_level, "%s: %s", self.log_name, line)
        except Exception:
            LOG.exception("Exception in _LogPipe thread %s", self.log_name)


class _LogPipe(_BaseLogPipe):
    def __init__(self, level):
        super(_LogPipe, self).__init__(level)
        self.read_fd, self.write_fd = os.pipe()

    def start(self, name):
        os.close(self.write_fd)
        super(_LogPipe, self).start(name)

    def pipe(self):
        return io.open(self.read_fd, 'r', errors='replace')


class BasePopen(object):
    def __init__(self, name, cmd, popen_kwargs):
        self.name = name
        self.cmd = cmd
        self.popen_kwargs = popen_kwargs
        self.stdin = None
        self.stdout = None
        self.stderr = None

    def poll(self):
        raise NotImplementedError("poll")

    def wait(self):
        raise NotImplementedError("wait")

    def terminate(self):
        raise NotImplementedError("terminate")

    def communicate(self):
        raise NotImplementedError("communicate")


class LocalPopen(BasePopen):
    def __init__(self, name, cmd, popen_kwargs):
        super(LocalPopen, self).__init__(name, cmd, popen_kwargs)
        self._popen_obj = None
        self.popen_kwargs.setdefault('close_fds', True)
        self._pipe_stdout, self._pipe_stderr = self._create_pipes()
        self._start()

    def _create_pipes(self):
        if 'stdout' not in self.popen_kwargs:
            pipe_stdout = _LogPipe(logging.INFO)
            self.popen_kwargs['stdout'] = pipe_stdout.write_fd
        else:
            pipe_stdout = None
        if 'stderr' not in self.popen_kwargs:
            pipe_stderr = _LogPipe(logging.ERROR)
            self.popen_kwargs['stderr'] = pipe_stderr.write_fd
        else:
            pipe_stderr = None
        return pipe_stdout, pipe_stderr

    def _start(self):
        if 'stdin' not in self.popen_kwargs:
            orig_preexec = self.popen_kwargs.get('preexec_fn')
            self.popen_kwargs['preexec_fn'] = functools.partial(
                _close_stdin, orig_preexec)
        self._popen_obj = subprocess.Popen(self.cmd, **self.popen_kwargs)
        self.name = "%s[%d]" % (self.name, self._popen_obj.pid)
        if 'stdin' in self.popen_kwargs:
            self.stdin = self._popen_obj.stdin
        if self._pipe_stdout:
            self._pipe_stdout.start(self.name + " stdout")
        else:
            self.stdout = self._popen_obj.stdout
        if self._pipe_stderr:
            self._pipe_stderr.start(self.name + " stderr")
        else:
            self.stderr = self._popen_obj.stderr

    def poll(self):
        return self._popen_obj.poll()

    def wait(self):
        return self._popen_obj.wait()

    def terminate(self):
        return self._popen_obj.terminate()

    def communicate(self):
        return self._popen_obj.communicate()


@contextlib.contextmanager
def popen(cmd, **kwargs):
    name = kwargs.pop('name', cmd[0])
    proc = LocalPopen(name, cmd, kwargs)
    LOG.info('Started process %s: %s', proc.name,
             " ".join(map(pipes.quote, cmd)))
    try:
        yield proc
    except Exception:
        rv = proc.poll()
        if rv is None:
            LOG.info("Terminating process %s", name)
            proc.terminate()
        else:
            LOG.error("Process %s finished with return value %s", name, rv)
        raise
    if 'stdin' in kwargs:
        proc.stdin.close()
    try:
        rv = proc.wait()
    except Exception:
        LOG.exception("Failed to wait for processs %s to finish", name)
        raise
    LOG.info("Process %s finished with return value %s", name, rv)
    if rv:
        raise subprocess.CalledProcessError(rv, name)


def call(cmd, **kwargs):
    with popen(cmd, **kwargs) as proc:
        return proc.communicate()
