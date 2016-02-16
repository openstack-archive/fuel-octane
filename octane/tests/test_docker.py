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

import mock
import pytest

from octane.util import docker
from octane.util import subprocess


@pytest.fixture()
def roll_back_get_docker_container_names_flag(request):
    base = docker.get_docker_container_names.use_without

    def foo():
        docker.get_docker_container_names.use_without = base

    request.addfinalizer(foo)


pytestmark = pytest.mark.usefixtures(
    "roll_back_get_docker_container_names_flag")


def test_get_container_names(mocker):

    def foo(call_args, *args, **kwargs):
        if '--format="{{.Names}}"' in call_args:
            raise subprocess.CalledProcessError(2, call_args)
        return ("NAMES\nfuel-core-container_1\nfuel-core-container_2", None)

    sub_mock = mocker.patch("octane.util.subprocess.call", side_effect=foo)
    assert not docker.get_docker_container_names.use_without
    assert ["container_1", "container_2"] == \
        docker.get_docker_container_names()
    sub_mock.assert_has_calls([
        mock.call(
            ["docker", "ps", '--all', '--format="{{.Names}}"'],
            stdout=subprocess.PIPE
        ), mock.call(
            ["docker", "ps", '--all'],
            stdout=subprocess.PIPE
        )])
    assert 2 == sub_mock.call_count
    assert docker.get_docker_container_names.use_without


def test_get_container_names_with_format(mocker):
    sub_mock = mocker.patch(
        "octane.util.subprocess.call",
        return_value=("fuel-core-container_1\nfuel-core-container_2\n\n",
                      None))
    assert not docker.get_docker_container_names.use_without
    assert ["container_1", "container_2"] == \
        docker.get_docker_container_names()
    assert not docker.get_docker_container_names.use_without
    sub_mock.assert_called_once_with(
        ["docker", "ps", '--all', '--format="{{.Names}}"'],
        stdout=subprocess.PIPE)


def test_wait_for_container(mocker):
    mock_sleep = mocker.patch('time.sleep')
    mock_popen = mocker.patch('octane.util.subprocess.popen')
    mock_popen.mock_add_spec(['__enter__', '__exit__'], spec_set=True)
    proc = mock_popen.return_value.__enter__.return_value
    proc.mock_add_spec(
        subprocess.BasePopen('name', ['cmd'], {'popen': 'kwargs'}),
        spec_set=True)
    proc.communicate.side_effect = [
        ("ActiveState=activating\n\n", None),
        ("ActiveState=active\n\n", None),
    ]

    mock_subprocess_call = mocker.patch('octane.util.subprocess.call')
    mock_subprocess_call.side_effect = [
        None, subprocess.CalledProcessError(1, "test_error")
    ]
    pytest.set_trace()
    docker.wait_for_container('test_container')
    assert 2 == proc.communicate.call_count \
        == mock_subprocess_call.call_count == mock_sleep.call_count
