# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import pytest

from octane.helpers import sync_glance_images


def test_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.sync_images.sync_glance_images')
    octane_app.run(['sync-images', '1', '2', 'br-mgmt'])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, 2, 'br-mgmt')


def test_prepare_parser(mocker, octane_app):
    m = mocker.patch('octane.commands.sync_images.prepare')
    octane_app.run(['sync-images-prepare', '1', '2'])
    assert not octane_app.stdout.getvalue()
    assert not octane_app.stderr.getvalue()
    m.assert_called_once_with(1, 2)


@pytest.mark.parametrize("yaml,expected", [
    ({'network_scheme': {'endpoints': {'MY_EP': {'IP': ['1.2.3.4/24']}}}},
     '1.2.3.4'),
    ({'network_scheme': {'endpoints': {'MY_EP1': {'IP': ['1.2.3.4/24']}}}},
     None),
])
def test_get_endpoint_ip(yaml, expected):
    result = sync_glance_images.get_endpoint_ip('MY_EP', yaml)
    assert result == expected


def test_get_swift_object(mock_subprocess, mock_ssh_call_output, node):
    mock_ssh_call_output.return_value = 'id1\nid2\n'
    res = sync_glance_images.get_swift_objects(
        node, 'tenant', 'user', 'password', 'token', 'container')
    assert not mock_subprocess.called
    assert mock_ssh_call_output.call_args_list == [
        mock.call(["sh", "-c", mock.ANY], node=node)]
    assert res == ['id1', 'id2']


def test_download_image(mock_subprocess, mock_ssh_call, node):
    mock_ssh_call.return_value = 'id1\nid2\n'
    sync_glance_images.download_image(
        node, 'tenant', 'user', 'password', 'token', 'container', 'id')
    assert not mock_subprocess.called
    assert mock_ssh_call.call_args_list == [
        mock.call(["sh", "-c", mock.ANY], node=node)]
