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

from octane.util import docker


def test_get_container_names(mocker):
    with_mock = mocker.patch(
        "octane.util.docker.get_docker_container_names_with_format",
        side_effect=Exception("Test"))
    without_mock = mocker.patch(
        "octane.util.docker.get_docker_container_names_without_format")
    docker.get_docker_container_names()
    with_mock.assert_called_once_with()
    without_mock.assert_called_once_with()
    assert docker.get_docker_container_names.use_without
    with_mock.reset_mock()
    without_mock.reset_mock()
    docker.get_docker_container_names()
    assert not with_mock.called
    without_mock.assert_called_once_with()
    assert docker.get_docker_container_names.use_without
