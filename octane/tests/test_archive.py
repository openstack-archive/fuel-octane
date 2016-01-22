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
import mock
import os
import pytest
import random

from octane.util import archivate
from octane.util import subprocess


def test_archivate_dirs_no_paths(mocker):
    test_archive = mocker.Mock()
    mocker.patch("os.path.exists", return_value=False)
    archivate.archive_dirs(test_archive, "/path", "tag")
    assert not test_archive.add.called


@pytest.mark.parametrize("directories,links,files", [
    (["dir_1", "dir_2"], ["link_1", "link_2"], ["file_1", "file_2"]),
    (["dir_1", "dir_2", "dir_3", "dir_4"], [], []),
    ([], ["link_1", "link_2", "link_3"], []),
    ([], [], ["file_1", "file_2", "file_3"]),
])
def test_archivate_dirs(mocker, directories, links, files):
    test_archive = mocker.Mock()
    path = "/path"
    tag = "tag"
    mocker.patch("os.path.exists", return_value=True)

    def contains(lst):
        def foo(x):
            return x in [os.path.join(path, d) for d in lst]
        return foo

    mocker.patch("os.path.isdir", side_effect=contains(directories))
    mocker.patch("os.path.islink", side_effect=contains(links))
    in_path = directories + links + files
    random.shuffle(in_path)
    mocker.patch("os.listdir", return_value=in_path)
    archivate.archive_dirs(test_archive, path, tag)
    assert len(test_archive.add.call_args_list) == len(directories)
    for directory in directories:
        test_archive.add.assert_has_calls([
            mock.call(
                os.path.join(path, directory),
                "{0}/{1}".format(tag, directory))
        ])


def test_archivate_container_cmd_output(mocker):
    test_archive = mocker.Mock()
    container = "test_container"
    cmd = ["test", "cmd"]
    filename = "archive_path"
    output_data = "output_data"
    docker_runnner = mocker.patch(
        "octane.util.docker.run_in_container",
        return_value=(output_data, None))
    io_mock = mocker.patch("io.BytesIO", return_value=io.BytesIO())
    mock_tar = mocker.patch("tarfile.TarInfo")
    archivate.archivate_container_cmd_output(
        test_archive, container, cmd, filename)

    docker_runnner.assert_called_once_with(
        container, cmd, stdout=subprocess.PIPE)
    io_mock.assert_called_once_with()
    mock_tar.assert_called_once_with(filename)
    tar_info = mock_tar.return_value
    assert tar_info.size == len(output_data)
    test_archive.addfile.assert_called_once_with(
        tar_info, io_mock.return_value)
    assert io_mock.return_value.getvalue() == output_data
