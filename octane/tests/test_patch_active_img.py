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

from octane.commands import patch_active_image
from octane import magic_consts


@pytest.mark.parametrize("root_img", ["root_img_path"])
@pytest.mark.parametrize("patched_img", ["patch_img_path"])
@pytest.mark.parametrize("patches", [("patch_1", ), ("patch_1", "patch_2")])
def test_patch_squashfs(mocker, root_img, patched_img, patches):
    temp_dir_mock = mocker.patch("octane.util.tempfile.temp_dir")
    temp_dir_mock.return_value.__enter__ = temp_dir_mock
    subprocess_mock = mocker.patch("octane.util.subprocess.call")
    patch_apply_mock = mocker.patch("octane.util.patch.patch_apply")
    patch_active_image._patch_squashfs(root_img, patched_img, *patches)
    patch_apply_mock.assert_called_once_with(
        temp_dir_mock.return_value, patches)
    assert [
        mock.call([
            "unsquashfs", "-f", "-d", temp_dir_mock.return_value, root_img
        ]),
        mock.call([
            "mksquashfs", temp_dir_mock.return_value, patched_img
        ]),
    ] == subprocess_mock.call_args_list


@pytest.mark.parametrize("src", ["src_data"])
@pytest.mark.parametrize("dst", ["dst_data"])
@pytest.mark.parametrize("root_fs_path", ["root_fs_path"])
def test_mk_metadata(mocker, mock_open, src, dst, root_fs_path):
    os_size_mock = mocker.patch("os.path.getsize")
    calc_md5 = mocker.patch("octane.commands.patch_active_image.calculate_md5")
    test_uuid = "123-123"
    uri = "path/{uuid}/qwer"
    data = {
        "uuid": test_uuid,
        "label": "test_label",
        "modules": {
            "rootfs": {
                "raw_size": 123123,
                "raw_md5": 123123,
                "uri": uri.format(uuid=test_uuid)
            }
        }
    }
    load_mock = mocker.patch("yaml.load", return_value=data)
    dump_mock = mocker.patch("yaml.dump")
    uuid_mock = mocker.patch("uuid.uuid1", return_value="my_generated_uuid")
    results = data.copy()
    patch_active_image._mk_metadata(src, dst, root_fs_path)
    results["label"] = patch_active_image.IMAGE_LABEL
    results["uuid"] = uuid_mock.return_value
    results["modules"]["rootfs"]["raw_size"] = os_size_mock.return_value
    results["modules"]["rootfs"]["raw_md5"] = calc_md5.return_value
    results["modules"]["rootfs"]["uri"] = uri.format(
        uuid=uuid_mock.return_value)
    dump_mock.assert_called_once_with(results, mock_open.return_value)
    assert [mock.call(src), mock.call(dst, "w")] == mock_open.call_args_list
    load_mock.assert_called_once_with(mock_open.return_value)


@pytest.mark.parametrize("work_dir", ["/working_dir"])
def test_patch_img(mocker, work_dir):
    temp_dir_mock = mocker.patch("octane.util.tempfile.temp_dir")
    temp_dir_mock.return_value.__enter__.return_value = work_dir
    mock_patch_sqfs = mocker.patch(
        "octane.commands.patch_active_image._patch_squashfs")
    mock_patch_mk_metadata = mocker.patch(
        "octane.commands.patch_active_image._mk_metadata")
    mock_named_temp = mocker.patch("tempfile.NamedTemporaryFile")
    mock_named_temp.return_value.__enter__.return_value = \
        mock_named_temp.return_value
    mock_tarfile = mocker.patch("tarfile.open")
    mock_tarfile.return_value.__enter__.return_value = \
        mock_tarfile.return_value
    subprocess_mock = mocker.patch("octane.util.subprocess.call")

    root_img = os.path.join(magic_consts.ACTIVE_IMG_PATH, "root.squashfs")
    patch_file = os.path.join(magic_consts.CWD, "patches/fuel_agent/patch")
    patched_img = os.path.join(work_dir, "root.squashfs")

    patch_active_image.patch_img()

    mock_patch_sqfs.assert_called_once_with(root_img, patched_img, patch_file)
    mock_patch_mk_metadata.assert_called_once_with(
        os.path.join(magic_consts.ACTIVE_IMG_PATH, "metadata.yaml"),
        os.path.join(work_dir, "metadata.yaml"),
        patched_img
    )
    mock_named_temp.assert_called_once_with()
    mock_tarfile.assert_called_once_with(
        name=mock_named_temp.return_value.name,
        mode="w:gz")
    arch_add_calls = ([
        mock.call(os.path.join(work_dir, "metadata.yaml"), "metadata.yaml"),
        mock.call(os.path.join(work_dir, "root.squashfs"), "root.squashfs"),
    ] + [
        mock.call(os.path.join(magic_consts.ACTIVE_IMG_PATH, p), p)
        for p in ["vmlinuz", "initrd.img"]
    ])
    mock_tarfile.return_value.add.assert_has_calls(
        arch_add_calls, any_order=True)

    subprocess_mock.assert_called_once_with([
        "fuel-bootstrap", "import", mock_named_temp.return_value.name
    ])


def test_parser(mocker, octane_app):
    patch_img_mock = mocker.patch(
        "octane.commands.patch_active_image.patch_img")
    octane_app.run(["patch-active-img"])
    patch_img_mock.assert_called_once_with()
