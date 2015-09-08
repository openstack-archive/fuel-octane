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

import functools
import io

import mock
import pytest

from octane import app
from octane.util import ssh
from octane.util import subprocess


class SafeOctaneApp(app.OctaneApp):
    def run(self, argv):
        try:
            super(SafeOctaneApp, self).run(argv)
        except SystemExit as e:
            assert e.code == 0


@pytest.fixture
def octane_app():
    return SafeOctaneApp(stdin=io.BytesIO(), stdout=io.BytesIO(),
                         stderr=io.BytesIO())


@pytest.fixture
def mock_open(mocker):
    mopen = mocker.patch('__builtin__.open')
    mopen.return_value.__enter__.return_value = mopen.return_value
    return mopen


@pytest.fixture
def node():
    # TODO: Be more specific about data and id
    return mock.Mock('a_node', spec_set=['data', 'id'])


def assert_popen_args(expected_kwargs, cmd, **kwargs):
    assert isinstance(cmd, list)
    for e in cmd:
        assert isinstance(e, str)
    assert expected_kwargs.issuperset(kwargs.keys())
    if 'popen_class' in expected_kwargs:
        assert kwargs.get('popen_class') in (None, ssh.SSHPopen)
    return mock.DEFAULT


def patch_subprocess_call(mocker, func, expected_kwargs):
    popen = mocker.patch(func)
    popen.mock_add_spec(['__enter__', '__exit__'], spec_set=True)
    popen.side_effect = functools.partial(assert_popen_args, expected_kwargs)
    return popen


def patch_subprocess_popen(mocker, func, expected_kwargs):
    popen = patch_subprocess_call(mocker, func, expected_kwargs)
    proc = popen.return_value.__enter__.return_value
    proc.mock_add_spec(
        subprocess.BasePopen('name', ['cmd'], {'popen': 'kwargs'}),
        spec_set=True,
    )
    return popen

ALL_POPEN_KWARGS = set([
    'stdin', 'stdout', 'stderr', 'shell', 'cwd',
])


@pytest.fixture
def mock_subprocess(mocker):
    return patch_subprocess_popen(
        mocker, 'octane.util.subprocess.popen', ALL_POPEN_KWARGS,
    )

ALL_SSH_KWARGS = set([
    'stdin', 'stdout', 'stderr', 'node', 'parse_levels',
])


@pytest.fixture
def mock_ssh_popen(mocker):
    return patch_subprocess_popen(
        mocker, 'octane.util.ssh.popen', ALL_SSH_KWARGS,
    )


@pytest.fixture
def mock_ssh_call(mocker):
    return patch_subprocess_call(
        mocker, 'octane.util.ssh.call',
        ALL_SSH_KWARGS,
    )


@pytest.fixture
def mock_ssh_call_output(mocker):
    return patch_subprocess_call(
        mocker, 'octane.util.ssh.call_output',
        ALL_SSH_KWARGS.difference(['stdout']),
    )
