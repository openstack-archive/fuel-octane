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

from octane.util import patch


@pytest.mark.parametrize("patches", [("patch_1", ), ("patch_1", "patch_2")])
@pytest.mark.parametrize("cwd", ["test_dir"])
@pytest.mark.parametrize("is_exception", [True, False])
def test_applied_context_manager(mocker, patches, cwd, is_exception):
    patch_mock = mocker.patch("octane.util.patch.patch_apply")

    class TestException(Exception):
        pass

    if is_exception:
        with pytest.raises(TestException):
            with patch.applied_patch(cwd, *patches):
                raise TestException
    else:
        with patch.applied_patch(cwd, *patches):
            pass
    assert [
        mock.call(cwd, patches),
        mock.call(cwd, patches, revert=True)
    ] == patch_mock.call_args_list


@pytest.mark.parametrize(
    "files", [["a_file"], ["b_file"], [], ["a_fiele", "b_file"]])
def test_get_filenames_from_single_patch(mock_open, files):

    test_patch = \
        b"diff --git a/a_file.txt b/a_file.txt\nindex 33..c3 100644"
    files_patch = b'\n'.join([b"--- {0}\n+++ {0}".format(f) for f in files])
    mock_open.return_value = io.BytesIO(
        b"{0}\n{1}".format(test_patch, files_patch))
    patch_name = "test_file.path"
    assert files == patch.get_filenames_from_single_patch(patch_name)
    mock_open.assert_called_once_with(patch_name)


@pytest.mark.parametrize("patches_f_names", [
    [],
    [("file_1", ["a", "b", "c"])],
    [
        ("fiel_1", ["a", "b", "c"]),
        ("file_2", ["d", "e", "f"])
    ]
])
@pytest.mark.parametrize("prefix", ["/test_prefix", "/test_prefix/"])
@pytest.mark.parametrize("prefix_add", [True, False])
def test_get_filenames_from_patches(mock, patches_f_names, prefix, prefix_add):
    patches = []
    files = []
    return_f = []
    for p, fs in patches_f_names:
        patches.append(p)
        if prefix_add:
            return_f.append([os.path.join(prefix, i) for i in fs])
        else:
            return_f.append(fs)
        files.extend(fs)
    mock.patch(
        "octane.util.patch.get_filenames_from_single_patch",
        side_effect=return_f)
    assert files == patch.get_filenames_from_patches(prefix, *patches)
