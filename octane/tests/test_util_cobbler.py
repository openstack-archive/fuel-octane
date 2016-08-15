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

from octane.util import cobbler


@pytest.mark.parametrize(("astute_dict", "expected_profile"), [
    ({}, "ubuntu_bootstrap"),
    ({"bootstrap_profile": "fake_profile"}, "fake_profile"),
])
def test_get_default_profile(mocker, astute_dict, expected_profile):
    mock_astute = mocker.patch("octane.util.helpers.get_astute_dict",
                               return_value=astute_dict)
    default_profile = cobbler.get_default_profile()
    assert default_profile == expected_profile
    mock_astute.assert_called_once_with()


@pytest.mark.parametrize(("output", "status"), [
    ("", False),
    ("\n", False),
    ("profile\n", True),
    ("   profile  \n   ", True),
])
@pytest.mark.parametrize("name", ["bootstr", "ubutstrap"])
def test_profile_exists(mocker, output, status, name):
    mock_output = mocker.patch("octane.util.subprocess.call_output",
                               return_value=output)
    result = cobbler.profile_exists(name)
    assert result == status
    mock_output.assert_called_once_with(
        ["cobbler", "profile", "find", "--name", name])


@pytest.mark.parametrize("name", ["old_bootstr", "old_ubutstrap"])
@pytest.mark.parametrize("new_name", ["bootstr", "ubutstrap"])
def test_profile_copy(mocker, name, new_name):
    mock_call = mocker.patch("octane.util.subprocess.call")
    cobbler.profile_copy(name, new_name)
    mock_call.assert_called_once_with(
        ["cobbler", "profile", "copy", "--name", name, "--newname", new_name])


@pytest.mark.parametrize(("names", "expected_names"), [
    ("sys0\n sys1 \n\nsys2", ["sys0", "sys1", "sys2"]),
    ("node-1\nnode-2\n", ["node-1", "node-2"]),
])
@pytest.mark.parametrize("profile", ["old_bootstr", "old_ubutstrap"])
@pytest.mark.parametrize("new_profile", ["bootstr", "ubutstrap"])
def test_systems_edit_profile(mocker, names, expected_names,
                              profile, new_profile):
    mock_calls = mock.Mock()
    mocker.patch("octane.util.subprocess.call_output", new=mock_calls.output)
    mock_calls.output.return_value = names
    mocker.patch("octane.util.subprocess.call", new=mock_calls.call)
    cobbler.systems_edit_profile(profile, new_profile)
    assert mock_calls.mock_calls == [
        mock.call.output(["cobbler", "system", "find", "--profile", profile]),
    ] + [
        mock.call.call(["cobbler", "system", "edit",
                        "--name", name, "--profile", new_profile])
        for name in expected_names
    ]


@pytest.mark.parametrize("name", ["bootstrap"])
@pytest.mark.parametrize("exists", [True, False])
def test_profile_remove(mocker, name, exists):
    mock_call = mocker.patch("octane.util.subprocess.call")
    mock_exists = mocker.patch("octane.util.cobbler.profile_exists",
                               return_value=exists)
    cobbler.profile_remove(name)
    if exists:
        mock_call.assert_called_once_with(
            ["cobbler", "profile", "remove", "--name", name])
    else:
        assert not mock_call.called
    mock_exists.assert_called_once_with(name)


@pytest.mark.parametrize("exists", [True, False])
def test_rename_bootstrap_profile_for_systems(mocker, exists):
    mock_calls = mock.Mock()
    mocker.patch("octane.util.cobbler.profile_exists", new=mock_calls.exists)
    mock_calls.exists.return_value = exists
    mocker.patch("octane.util.cobbler.get_default_profile",
                 new=mock_calls.default)
    mock_calls.default.return_value = "ubuntu"
    mocker.patch("octane.util.cobbler.profile_copy", new=mock_calls.copy)
    mocker.patch("octane.util.cobbler.systems_edit_profile",
                 new=mock_calls.edit)
    mocker.patch("octane.util.cobbler.profile_remove", new=mock_calls.remove)

    with cobbler.rename_bootstrap_profile_for_systems():
        mock_calls.let()

    calls_enter = [
        mock.call.default(),
        mock.call.exists("bootstrap"),
    ]
    calls_exit = [
        mock.call.edit("bootstrap", "ubuntu"),
    ]
    if not exists:
        calls_enter.extend([
            mock.call.copy("ubuntu", "bootstrap"),
        ])
        calls_exit.extend([
            mock.call.remove("bootstrap"),
        ])
    expected_calls = calls_enter + [mock.call.let()] + calls_exit
    assert mock_calls.mock_calls == expected_calls
    if exists:
        assert not mock_calls.copy.called
        assert not mock_calls.remove.called
