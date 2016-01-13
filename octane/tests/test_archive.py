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
import random

from octane.util import archivate
from octane.util import subprocess


def test_archivate_dirs_no_paths(mocker):
    test_archive = mocker.Mock()
    mocker.patch("octane.util.archivate.os.path.exists", return_value=False)
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
    mocker.patch("octane.util.archivate.os.path.exists", return_value=True)
    mocker.patch(
        "octane.util.archivate.os.path.isdir",
        side_effect=lambda x: x in [os.path.join(path, d) for d in directories]
    )
    mocker.patch(
        "octane.util.archivate.os.path.islink",
        side_effect=lambda x: x in [os.path.join(path, l) for l in links]
    )
    in_path = directories + links + files
    random.shuffle(in_path)
    mocker.patch("octane.util.archivate.os.listdir", return_value=in_path)
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
        "octane.util.archivate.docker.run_in_container",
        return_value=(output_data, None))
    io_mock = mocker.patch("octane.util.archivate.io.BytesIO")
    mock_tar = mocker.patch("octane.util.archivate.tarfile.TarInfo")

    archivate.archivate_container_cmd_output(
        test_archive, container, cmd, filename)

    docker_runnner.assert_called_once_with(
        container, cmd, stdout=subprocess.PIPE)
    io_mock.assert_called_once_with()
    io_mock.return_value.write.assert_called_once_with(output_data)
    io_mock.return_value.seek.assert_called_once_with(0)
    mock_tar.assert_called_once_with(filename)
    tar_info = mock_tar.return_value
    assert tar_info.size == len(output_data)
    test_archive.addfile.assert_called_once_with(
        tar_info, io_mock.return_value)
