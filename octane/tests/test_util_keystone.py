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

import contextlib
import copy

import mock
import pytest

from octane.util import keystone


@contextlib.contextmanager
def verify_update_file(mocker, parameters, writes):
    mock_old = mock.Mock()
    mock_new = mock.Mock()

    mock_update_file = mocker.patch("octane.util.subprocess.update_file")
    mock_update_file.return_value.__enter__.return_value = (mock_old, mock_new)

    mock_iter_params = mocker.patch("octane.util.helpers.iterate_parameters")
    mock_iter_params.return_value = parameters

    expected_writes = [mock.call(call) for call in writes]

    yield mock_update_file

    mock_iter_params.assert_called_once_with(mock_old)
    assert mock_new.write.call_args_list == expected_writes


@pytest.mark.parametrize(("parameters", "writes"), [
    ([
        ("[identity]\n", "identity", None, None),
        ("default_domain_id = b5a5e858092d44ffbe2f3347831c5ca7\n",
         "identity", "default_domain_id", "b5a5e858092d44ffbe2f3347831c5ca7"),
    ], [
        "[identity]\n",
        "#default_domain_id = b5a5e858092d44ffbe2f3347831c5ca7\n",
    ]),
    ([
        ("[identity]\n", "identity", None, None),
    ], [
        "[identity]\n",
    ]),
])
def test_unset_default_domain_id(mocker, parameters, writes):
    with verify_update_file(mocker, parameters, writes) as mock_update_file:
        keystone.unset_default_domain_id("fakefilename")
    mock_update_file.assert_called_once_with("fakefilename")


def test_admin_token_auth(mocker):
    mock_calls = mock.Mock()
    mocker.patch("octane.util.keystone.add_admin_token_auth",
                 new=mock_calls.add)
    mocker.patch("octane.util.keystone.remove_admin_token_auth",
                 new=mock_calls.remove)
    mocker.patch("octane.util.subprocess.call", new=mock_calls.subprocess)
    with keystone.admin_token_auth("fakefilename", "fakepipelines"):
        mock_calls.let()
    expected_calls = [
        mock.call.add("fakefilename", "fakepipelines"),
        mock.call.let(),
        mock.call.remove("fakefilename", "fakepipelines"),
        mock.call.subprocess(["systemctl", "restart", "openstack-keystone"]),
    ]
    assert mock_calls.mock_calls == expected_calls


@pytest.mark.parametrize(("items", "expected_items"), [
    (
        [
            ["request_id", "token_auth"],
            ["admin_token_auth", "token_auth"],
        ],
        [
            ["request_id", "admin_token_auth", "token_auth"],
            ["admin_token_auth", "token_auth"],
        ],
    ),
])
def test_add_admin_token_auth(mocker, items, expected_items):
    items = copy.deepcopy(items)
    mock_replace = mocker.patch("octane.util.keystone.replace_pipeline_items")
    mock_replace.return_value.__enter__.return_value = items
    keystone.add_admin_token_auth("fakefilename", "fakepipelines")
    assert items == expected_items
    mock_replace.assert_called_once_with("fakefilename", "fakepipelines")


@pytest.mark.parametrize(("parameters", "writes"), [
    ([
        ("[pipeline:public_api]\n", "pipeline:public_api", None, None),
        ("pipeline = request_id admin_token_auth token_auth public_service\n",
         "pipeline:public_api", "pipeline",
         "request_id admin_token_auth token_auth public_service"),
        ("[pipeline:admin_api]\n", "pipeline:admin_api", None, None),
        ("pipeline = request_id token_auth admin_service\n",
         "pipeline:admin_api", "pipeline",
         "request_id token_auth admin_service"),
        ("[pipeline:api_v3]\n", "pipeline:api_v3", None, None),
        ("pipeline = request_id token_auth service_v3\n",
         "pipeline:api_v3", "pipeline",
         "request_id token_auth service_v3"),
    ], [
        "[pipeline:public_api]\n",
        "pipeline = request_id admin_token_auth token_auth public_service\n",
        "[pipeline:admin_api]\n",
        "pipeline = request_id admin_token_auth token_auth admin_service\n",
        "[pipeline:api_v3]\n",
        "pipeline = request_id token_auth service_v3\n",
    ])
])
def test_add_admin_token_auth_functional(mocker, parameters, writes):
    with verify_update_file(mocker, parameters, writes) as mock_update_file:
        keystone.add_admin_token_auth("fakefilename", [
            "pipeline:public_api",
            "pipeline:admin_api",
        ])
    mock_update_file.assert_called_once_with("fakefilename")


@pytest.mark.parametrize(("items", "expected_items"), [
    (
        [
            ["request_id", "token_auth"],
            ["admin_token_auth", "token_auth"],
        ],
        [
            ["request_id", "token_auth"],
            ["token_auth"],
        ],
    ),
])
def test_remove_admin_token_auth(mocker, items, expected_items):
    items = copy.deepcopy(items)
    mock_replace = mocker.patch("octane.util.keystone.replace_pipeline_items")
    mock_replace.return_value.__enter__.return_value = items
    keystone.remove_admin_token_auth("fakefilename", "fakepipelines")
    assert items == expected_items
    mock_replace.assert_called_once_with("fakefilename", "fakepipelines")


@pytest.mark.parametrize(("parameters", "writes"), [
    ([
        ("[pipeline:public_api]\n", "pipeline:public_api", None, None),
        ("pipeline = request_id admin_token_auth token_auth public_service\n",
         "pipeline:public_api", "pipeline",
         "request_id admin_token_auth token_auth public_service"),
        ("[pipeline:admin_api]\n", "pipeline:admin_api", None, None),
        ("pipeline = request_id token_auth admin_service\n",
         "pipeline:admin_api", "pipeline",
         "request_id token_auth admin_service"),
        ("[pipeline:api_v3]\n", "pipeline:api_v3", None, None),
        ("pipeline = request_id admin_token_auth token_auth service_v3\n",
         "pipeline:api_v3", "pipeline",
         "request_id admin_token_auth token_auth service_v3"),
    ], [
        "[pipeline:public_api]\n",
        "pipeline = request_id token_auth public_service\n",
        "[pipeline:admin_api]\n",
        "pipeline = request_id token_auth admin_service\n",
        "[pipeline:api_v3]\n",
        "pipeline = request_id admin_token_auth token_auth service_v3\n",
    ])
])
def test_remove_admin_token_auth_functional(mocker, parameters, writes):
    with verify_update_file(mocker, parameters, writes) as mock_update_file:
        keystone.remove_admin_token_auth("fakefilename", [
            "pipeline:public_api",
            "pipeline:admin_api",
        ])
    mock_update_file.assert_called_once_with("fakefilename")


@pytest.mark.parametrize(("parameters", "writes"), [
    ([
        ("[pipeline:public_api]\n", "pipeline:public_api", None, None),
        ("pipeline = token_auth public_service\n",
         "pipeline:public_api", "pipeline", "token_auth public_service"),
        ("[pipeline:admin_api]\n", "pipeline:admin_api", None, None),
        ("pipeline = request_id token_auth admin_service\n",
         "pipeline:admin_api", "pipeline",
         "request_id token_auth admin_service"),
        ("[pipeline:api_v3]\n", "pipeline:api_v3", None, None),
        ("pipeline = token_auth service_v3\n",
         "pipeline:api_v3", "pipeline", "token_auth service_v3"),
    ], [
        "[pipeline:public_api]\n",
        "pipeline = token_auth public_service\n",
        "[pipeline:admin_api]\n",
        "pipeline = a token_auth admin_service c\n",
        "[pipeline:api_v3]\n",
        "pipeline = token_auth service_v3\n",
    ])
])
def test_replace_pipelines_items(mocker, parameters, writes):
    pipelines = ["pipeline:admin_api"]
    with verify_update_file(mocker, parameters, writes) as mock_update_file:
        with keystone.replace_pipeline_items("fakefilename", pipelines) as \
                pipeline_items:
            for items in pipeline_items:
                items.insert(0, "a")
                items.remove("request_id")
                items.append("c")
    mock_update_file.assert_called_once_with("fakefilename")
