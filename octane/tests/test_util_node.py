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
import io
import mock
import pytest

from octane.util import node as node_util
from octane.util import ssh


NODES = [
    {'fqdn': 'node-1',
     'network_data': [{'name': 'management', 'ip': '10.20.0.2'},
                      {'name': 'public', 'ip': '172.167.0.2'}]},
    {'fqdn': 'node-2',
     'network_data': [{'name': 'management', 'ip': '10.20.0.3'},
                      {'name': 'public', 'ip': '172.167.0.3'}]},
    {'fqdn': 'node-3',
     'network_data': [{'name': 'management', 'ip': '10.20.0.4'},
                      {'name': 'public', 'ip': '172.167.0.4'}]},
]


@pytest.mark.parametrize('node_data,network_name,expected_ip', [
    (NODES[0], 'management', '10.20.0.2'),
    (NODES[0], 'storage', None),
    ({'network_data': []}, 'management', None),
])
def test_get_ip(node_data, network_name, expected_ip):
    node = create_node(node_data)
    ip = node_util.get_ip(network_name, node)
    assert ip == expected_ip


def create_node(data):
    return mock.Mock(data=data, spec_set=['data'])


@pytest.fixture
def nodes():
    return map(create_node, NODES)


@pytest.mark.parametrize("network_name,expected_ips", [
    ('management', ['10.20.0.2', '10.20.0.3', '10.20.0.4']),
    ('public', ['172.167.0.2', '172.167.0.3', '172.167.0.4']),
])
def test_get_ips(nodes, network_name, expected_ips):
    ips = node_util.get_ips(network_name, nodes)
    assert ips == expected_ips


def test_get_hostnames(nodes):
    hostnames = node_util.get_hostnames(nodes)
    assert hostnames == ['node-1', 'node-2', 'node-3']


def test_tar_files(node, mock_ssh_popen, mock_open):
    content = b'fake data\nin\nthe\narchive'

    proc = mock_ssh_popen.return_value.__enter__.return_value
    proc.stdout = io.BytesIO(content)
    buf = io.BytesIO()
    mock_open.return_value.write.side_effect = buf.write

    node_util.tar_files('filename', node, 'a.file', 'b.file')

    mock_ssh_popen.assert_called_once_with(
        ['tar', '-czvP', 'a.file', 'b.file'],
        stdout=ssh.PIPE, node=node)
    mock_open.assert_called_once_with('filename', 'wb')
    assert buf.getvalue() == content


def test_untar_files(node, mock_ssh_popen, mock_open):
    content = b'fake data\nin\nthe\narchive'

    proc = mock_ssh_popen.return_value.__enter__.return_value
    buf = io.BytesIO()
    proc.stdin.write = buf.write
    mock_open.return_value = io.BytesIO(content)

    node_util.untar_files('filename', node)

    mock_ssh_popen.assert_called_once_with(['tar', '-xzv', '-C', '/'],
                                           stdin=ssh.PIPE, node=node)
    mock_open.assert_called_once_with('filename', 'rb')
    assert buf.getvalue() == content


@contextlib.contextmanager
def _check_upgrade_levels(mocker, node, content, expected_content):
    mock_sftp = mocker.patch('octane.util.ssh.sftp')

    old = io.BytesIO(content)
    mock_new = mocker.Mock()
    buf = io.BytesIO()
    mock_new.write = buf.write
    mock_update_file = mocker.patch('octane.util.ssh.update_file')
    mock_update_file.return_value.__enter__.return_value = (old, mock_new)

    yield

    mock_sftp.assert_called_once_with(node)
    mock_update_file.assert_called_once_with(mock_sftp.return_value,
                                             '/etc/nova/nova.conf')
    assert buf.getvalue() == expected_content


NOVA_DEFAULT = b"#\u0444\n[DEFAULT]\ndebug = True\n"
NOVA_WITH_EMPTY_LEVELS = NOVA_DEFAULT + b"[upgrade_levels]\n"
NOVA_WITH_KILO_LEVELS = NOVA_WITH_EMPTY_LEVELS + b"compute=kilo\n"


@pytest.mark.parametrize("content,expected_content", [
    (NOVA_DEFAULT, NOVA_DEFAULT),
    (NOVA_WITH_EMPTY_LEVELS, NOVA_WITH_KILO_LEVELS),
])
def test_add_compute_upgrade_levels(mocker, node, content, expected_content):
    with _check_upgrade_levels(mocker, node, content, expected_content):
        node_util.add_compute_upgrade_levels(node, 'kilo')


@pytest.mark.parametrize("content,expected_content", [
    (NOVA_DEFAULT, NOVA_DEFAULT),
    (NOVA_WITH_EMPTY_LEVELS, NOVA_WITH_EMPTY_LEVELS),
    (NOVA_WITH_KILO_LEVELS, NOVA_WITH_EMPTY_LEVELS),
])
def test_remove_compute_upgrade_levels(mocker, node, content,
                                       expected_content):
    with _check_upgrade_levels(mocker, node, content, expected_content):
        node_util.remove_compute_upgrade_levels(node)


NOVA_LIVE_MIGRATION_FLAG = b"    live_migration_flag="
NOVA_LIVE_MIGRATION_ENABLED = NOVA_LIVE_MIGRATION_FLAG + \
    b"FLAG1,VIR_MIGRATE_LIVE,FLAG2\n"
NOVA_NO_LIVE_MIGRATION_FLAG = b"no_live_migration_flag\n"
NOVA_EMPTY = b""


@pytest.mark.parametrize("content,expected_res", [
    (NOVA_LIVE_MIGRATION_ENABLED, True),
    (NOVA_LIVE_MIGRATION_FLAG, False),
    (NOVA_NO_LIVE_MIGRATION_FLAG, False),
    (NOVA_EMPTY, False),
])
def test_is_live_migration_supported(mocker, node, content, expected_res):
    mock_sftp = mocker.patch("octane.util.ssh.sftp")
    mock_sftp.return_value.open.return_value = io.BytesIO(content)

    res = node_util.is_live_migration_supported(node)
    assert res == expected_res
