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
import os
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


test_container = "test_container"
attempts = 2
delay = 0


def test_wait_for_start_container(mocker, mock_subprocess):
    proc = mock_subprocess.return_value.__enter__.return_value
    proc.communicate.side_effect = [
        ("ActiveState=activating\n\n", None),
        ("ActiveState=active\n\n", None),
    ]

    docker._wait_for_start_container(test_container, attempts, delay)
    assert 2 == mock_subprocess.call_count


def test_wait_for_puppet_in_container(mocker, mock_subprocess):
    mock_subprocess.side_effect = [
        mock.DEFAULT,
        subprocess.CalledProcessError(1, 'test_error')
    ]
    docker._wait_for_puppet_in_container(test_container, attempts, delay)
    assert 2 == mock_subprocess.call_count


@pytest.mark.parametrize(
    "container_id,stop_by_docker",
    [('\n', False), ("123", True), ("123\n", True)])
@pytest.mark.parametrize("container_name", ["container_name"])
def test_docker_stop(
        mocker, mock_subprocess, container_id, container_name, stop_by_docker):
    mock_subprocess_call_output = mocker.patch(
        "octane.util.subprocess.call_output", return_value=container_id)
    mock_stop_action = mocker.patch("octane.util.docker._container_action")
    docker.stop_container(container_name)
    mock_stop_action.assert_called_once_with(container_name, "stop")
    mock_subprocess_call_output.assert_called_once_with([
        'docker',
        'ps',
        '--filter',
        'name={0}'.format(container_name),
        '--format',
        '{{.ID}}'
    ])
    if stop_by_docker:
        mock_subprocess.assert_called_once_with(
            ["docker", "stop", container_id.strip()])
    else:
        assert not mock_subprocess.called


@pytest.mark.parametrize("container", ["container"])
@pytest.mark.parametrize("prefix", ["prefix"])
@pytest.mark.parametrize("patches", [("patch_1", ), ("patch_1", "patch_2")])
@pytest.mark.parametrize("revert", [None, True, False])
@pytest.mark.parametrize("files", [[], ["file_1"], ["file_1", "file_2"]])
def test_apply_patches(mocker, container, prefix, patches, revert, files):
    kwargs = {}
    if revert is not None:
        kwargs['revert'] = revert

    mock_get_filenames = mocker.patch(
        "octane.util.patch.get_filenames_from_patches", return_value=files)
    mock_tempdir = mocker.patch("octane.util.tempfile.temp_dir")
    get_files_mock = mocker.patch("octane.util.docker.get_files_from_docker")
    put_files_mock = mocker.patch("octane.util.docker.put_files_to_docker")
    patch_mock = mocker.patch("octane.util.patch.patch_apply")

    docker.apply_patches(container, prefix, *patches, **kwargs)

    mock_get_filenames.assert_called_once_with(prefix, *patches)
    if files:
        mock_tempdir.assert_called_once_with(prefix='octane_docker_patches.')
        temp_dir = mock_tempdir.return_value.__enter__.return_value
        get_files_mock.assert_called_once_with(
            container, [os.path.join(prefix, f) for f in files], temp_dir)
        patch_mock.assert_called_once_with(temp_dir, patches, bool(revert))
        put_files_mock.assert_called_once_with(container, "/", temp_dir)


@pytest.mark.parametrize("container", ["container_name"])
@pytest.mark.parametrize("prefix", ["prefix_name"])
@pytest.mark.parametrize("patches", [["patch_1"], ["patch_1", "patch_2"]])
@pytest.mark.parametrize("error", [True, False])
def test_applied_patches(mocker, container, prefix, patches, error):

    class TestException(Exception):
        pass

    apply_patches = mocker.patch("octane.util.docker.apply_patches")
    if error:
        with pytest.raises(TestException):
            with docker.applied_patches(container, prefix, *patches):
                raise TestException()
    else:
        with docker.applied_patches(container, prefix, *patches):
            pass
    assert [
        mock.call(container, prefix, *patches),
        mock.call(container, prefix, *patches, revert=True)
    ] == apply_patches.call_args_list


@pytest.mark.parametrize("is_exception", [True, False])
@pytest.mark.parametrize("container", ["container"])
@pytest.mark.parametrize("patches", [("patch_1", ), ("patch_1", "patch_2")])
@pytest.mark.parametrize("service", ["service_1"])
@pytest.mark.parametrize("prefix ", ["prefix_1", "prefix_2", None])
def test_patch_container_service(
        mocker, patches, container, is_exception, service, prefix):
    patch_mock = mocker.patch("octane.util.docker.applied_patches")

    class TestException(Exception):
        pass

    docker_run_mock = mocker.patch("octane.util.docker.run_in_container")

    if is_exception:
        with pytest.raises(TestException):
            with docker.patch_container_service(
                    container, service, prefix, *patches):
                raise TestException
    else:
        with docker.patch_container_service(
                container, service, prefix, *patches):
            pass

    assert [
        mock.call(container, ["service", service, "restart"]),
        mock.call(container, ["service", service, "restart"])
    ] == docker_run_mock.call_args_list
    patch_mock.assert_called_once_with(container, prefix, *patches)


@pytest.mark.parametrize("container", ["container"])
@pytest.mark.parametrize("container_name", ["container_name"])
@pytest.mark.parametrize("is_exception", [True, False])
def test_destroyed_container(mocker, container, container_name, is_exception):
    subprocess_call_mock = mocker.patch("octane.util.subprocess.call")
    get_name_mock = mocker.patch(
        "octane.util.docker.get_docker_container_name",
        return_value=container_name)

    class TestException(Exception):
        pass

    if is_exception:
        with pytest.raises(TestException):
            with docker.destroyed_container(container):
                raise TestException
    else:
        with docker.destroyed_container(container):
            pass

    assert [
        mock.call(["dockerctl", "destroy", container_name]),
        mock.call(["dockerctl", "start", container]),
        mock.call(["dockerctl", "check", container]),
    ] == subprocess_call_mock.call_args_list

    get_name_mock.assert_called_once_with(container)
