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


class _LogPipe(threading.Thread):
    def __init__(self, level):
        super(_LogPipe, self).__init__()
        self.daemon = True
        self.log_name = None
        self.log_level = level
        self.read_fd, self.write_fd = os.pipe()

    def start(self, name):
        os.close(self.write_fd)
        self.log_name = name
        super(_LogPipe, self).start()

    def run(self):
        try:
            with io.open(self.read_fd, 'r', errors='replace') as pipe:
                for line in pipe:
                    if line.endswith('\n'):
                        line = line[:-1]
                    LOG.log(self.log_level, "%s: %s", self.log_name, line)
        except Exception:
            LOG.exception("Exception in _LogPipe thread %s", self.name)


@contextlib.contextmanager
def popen(cmd, **kwargs):
    name = kwargs.pop('name', cmd[0])
    kwargs.setdefault('close_fds', True)
    if 'stdin' not in kwargs:
        orig_preexec = kwargs.get('preexec_fn')
        kwargs['preexec_fn'] = functools.partial(_close_stdin, orig_preexec)
    if 'stdout' not in kwargs:
        pipe_stdout = _LogPipe(logging.INFO)
        kwargs['stdout'] = pipe_stdout.write_fd
    else:
        pipe_stdout = None
    if 'stderr' not in kwargs:
        pipe_stderr = _LogPipe(logging.ERROR)
        kwargs['stderr'] = pipe_stderr.write_fd
    else:
        pipe_stderr = None
    proc = subprocess.Popen(cmd, **kwargs)
    name = "%s[%d]" % (name, proc.pid)
    LOG.info('Started process %s: %s', name, " ".join(map(pipes.quote, cmd)))
    if pipe_stdout:
        pipe_stdout.start(name + " stdout")
    if pipe_stderr:
        pipe_stderr.start(name + " stderr")
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
    with popen(cmd, **kwargs):
        pass
