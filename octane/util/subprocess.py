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
import re
import subprocess
import threading

from octane.util import tempfile

LOG = logging.getLogger(__name__)
PIPE = subprocess.PIPE
CalledProcessError = subprocess.CalledProcessError


def _close_stdin(chain_fn=None):
    os.close(0)
    if chain_fn:
        chain_fn()


class _BaseLogPipe(threading.Thread):
    try:
        _levels = logging._nameToLevel
    except AttributeError:
        _levels = logging._levelNames

    def __init__(self, level, parse_levels=False):
        super(_BaseLogPipe, self).__init__()
        self.log_name = None
        self.log_level = level
        if not parse_levels:
            self.levels_re = None
        else:
            if parse_levels is True:
                # Date, time, PID, log level - default OpenStack log format
                parse_levels = '^[0-9/-]+ [0-9:.,]+ [0-9]+ (?P<level>[A-Z]+)'
            self.levels_re = re.compile(parse_levels)

    def start(self, name):
        self.log_name = name
        super(_BaseLogPipe, self).start()

    def run(self):
        try:
            with self.pipe() as pipe:
                for line in pipe:
                    if line.endswith('\n'):
                        line = line[:-1]
                    log_level = None
                    if self.levels_re is not None:
                        match = self.levels_re.match(line)
                        if match:
                            log_level = self._levels.get(match.group('level'))
                    if log_level is None:
                        log_level = self.log_level
                    LOG.log(log_level, "%s: %s", self.log_name, line)
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

    def close_stdin(self):
        raise NotImplementedError("close_stdin")

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

        stderr_level = self.popen_kwargs.pop('stderr_log_level', logging.ERROR)

        if 'stderr' not in self.popen_kwargs:
            pipe_stderr = _LogPipe(stderr_level)
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

    def close_stdin(self):
        self._popen_obj.stdin.close()

    def communicate(self):
        return self._popen_obj.communicate()


@contextlib.contextmanager
def popen(cmd, **kwargs):
    name = kwargs.pop('name', cmd[0])
    popen_class = kwargs.pop('popen_class', LocalPopen)
    proc = popen_class(name, cmd, kwargs)
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
    if kwargs.get('stdin') == PIPE:
        proc.close_stdin()
    try:
        rv = proc.wait()
    except Exception:
        LOG.exception("Failed to wait for processs %s to finish", name)
        raise
    LOG.info("Process %s finished with return value %s", name, rv)
    if rv:
        raise CalledProcessError(rv, name)


def call(cmd, **kwargs):
    with popen(cmd, **kwargs) as proc:
        return proc.communicate()


def call_output(cmd, **kwargs):
    return call(cmd, stdout=PIPE, **kwargs)[0]


class DontUpdateException(Exception):
    pass


@contextlib.contextmanager
def update_file(filename):
    old = open(filename, 'r')
    dirname = os.path.dirname(filename)
    prefix = ".{0}.".format(os.path.basename(filename))
    temp_filename = tempfile.get_tempname(dir=dirname, prefix=prefix)
    new = open(temp_filename, 'w')
    with contextlib.nested(old, new):
        try:
            yield old, new
        except DontUpdateException:
            os.unlink(temp_filename)
            return
        except Exception:
            os.unlink(temp_filename)
            raise
        stat = os.stat(filename)
        os.chmod(temp_filename, stat.st_mode)
        os.chown(temp_filename, stat.st_uid, stat.st_gid)
    bak_filename = filename + '.bak'
    os.rename(filename, bak_filename)
    os.rename(temp_filename, filename)
    os.unlink(bak_filename)
