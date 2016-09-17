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
import pytest

from octane.tests import util as test_util
from octane.util import node as node_util
from octane.util import ssh


NODES = [
    {'id': '1',
     'fqdn': 'node-1.domain.tld',
     'network_data': [{'name': 'management', 'ip': '10.20.0.2'},
                      {'name': 'public', 'ip': '172.167.0.2'}]},
    {'id': '2',
     'fqdn': 'node-2.domain.tld',
     'network_data': [{'name': 'management', 'ip': '10.20.0.3'},
                      {'name': 'public', 'ip': '172.167.0.3'}]},
    {'id': '3',
     'fqdn': 'node-3.domain.tld',
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
    return mock.Mock(data=data, spec_set=['data', 'env'])


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
    assert hostnames == ['node-1.domain.tld',
                         'node-2.domain.tld',
                         'node-3.domain.tld']


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


NOVA_DEFAULT = b"#\u0444\n[DEFAULT]\ndebug = True\n"
NOVA_WITH_EMPTY_LEVELS = NOVA_DEFAULT + b"[upgrade_levels]\n"
NOVA_WITH_JUNO_LEVELS = NOVA_WITH_EMPTY_LEVELS + b"compute=juno\n"
NOVA_WITH_KILO_LEVELS = NOVA_WITH_EMPTY_LEVELS + b"compute=kilo\n"
NOVA_BROKEN_LEVELS = NOVA_DEFAULT + b"compute=essex\n[upgrade_levels]\n"
NOVA_BROKEN_LEVELS_WITH_KILO = NOVA_BROKEN_LEVELS + b"compute=kilo\n"


@pytest.mark.parametrize("content,expected_content,filename", [
    (NOVA_DEFAULT, NOVA_WITH_KILO_LEVELS, '/etc/nova/nova.conf'),
    (NOVA_WITH_EMPTY_LEVELS, NOVA_WITH_KILO_LEVELS, '/etc/nova/nova.conf'),
    (NOVA_WITH_JUNO_LEVELS, NOVA_WITH_KILO_LEVELS, '/etc/nova/nova.conf'),
    (NOVA_BROKEN_LEVELS, NOVA_BROKEN_LEVELS_WITH_KILO, '/etc/nova/nova.conf'),
])
def test_add_compute_upgrade_levels(mocker, node, content, expected_content,
                                    filename):
    with test_util.mock_update_file(mocker, node, content, expected_content,
                                    filename):
        node_util.add_compute_upgrade_levels(node, 'kilo')


@pytest.mark.parametrize("content,expected_content,filename", [
    (NOVA_DEFAULT, NOVA_DEFAULT, '/etc/nova/nova.conf'),
    (NOVA_WITH_EMPTY_LEVELS, NOVA_WITH_EMPTY_LEVELS, '/etc/nova/nova.conf'),
    (NOVA_WITH_KILO_LEVELS, NOVA_WITH_EMPTY_LEVELS, '/etc/nova/nova.conf'),
    (NOVA_BROKEN_LEVELS_WITH_KILO, NOVA_WITH_EMPTY_LEVELS,
     '/etc/nova/nova.conf'),
])
def test_remove_compute_upgrade_levels(mocker, node, content,
                                       expected_content, filename):
    with test_util.mock_update_file(mocker, node, content, expected_content,
                                    filename):
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


@pytest.mark.parametrize('node_data,fuel_version,expected_name', [
    (NODES[0], '6.0', 'node-1'),
    (NODES[0], '6.1', 'node-1.domain.tld'),
    (NODES[0], 'invalid', None)
])
def test_get_nova_node_handle(mocker, node_data, fuel_version, expected_name):
    node = create_node(node_data)
    node.env.data.get.return_value = fuel_version
    if expected_name:
        name = node_util.get_nova_node_handle(node)
        assert name == expected_name
    else:
        with pytest.raises(Exception):
            node_util.get_nova_node_handle(node)


@pytest.mark.parametrize('stdout,nova_services_to_restart', [
    (
        "   [ + ] nova-service-1\n"
        "   [ + ] nova-service-2\n"
        "   [ - ] nova-service-3\n"
        "   [ - ] not-nova-service-1\n"
        "   [ + ] not-nova-service-2\n"
        "   [ + ] nova-service-4\n",
        [
            'nova-service-1',
            'nova-service-2',
            'nova-service-4',
        ]
    )
])
def test_restart_nova_services(mocker, node, stdout, nova_services_to_restart):
    call_output_mock = mocker.patch(
        "octane.util.ssh.call_output", return_value=stdout)
    call_mock = mocker.patch("octane.util.ssh.call")
    node_util.restart_nova_services(node)
    for service in nova_services_to_restart:
        call_mock.assert_any_call(["service", service, "restart"], node=node)
    call_output_mock.assert_called_once_with(
        ["service", "--status-all"], node=node)


@pytest.mark.parametrize(
    ("parameters", "parameters_to_get", "required", "ensure", "error"), [
        ({
            "opt1": "value1",
            "opt2": "value2",
        }, {
            "opt1": [("section1", "option1")],
            "opt2": [("section2", "option2")],
        }, ("section1/option1", "section2/option2"), True, False),

        ({}, {
            "opt1": [("section1", "option1")],
        }, ("section1/option1"), True, True),

        ({}, {
            "opt1": [("section1", "option1")],
        }, (), False, False),
    ]
)
def test_get_parameters(mocker, parameters, parameters_to_get, required,
                        ensure, error):
    mock_node = mock.Mock(data={"id": 1})
    filename = "fake/filename.conf"
    mock_sftp = mocker.patch("octane.util.ssh.sftp")
    mock_get = mocker.patch("octane.util.helpers.get_parameters")
    mock_get.return_value = parameters
    if ensure and error:
        msg = ("Could not get parameters from the file "
               "node-1[fake/filename.conf]: {parameters}"
               .format(parameters=", ".join(required)))
        with pytest.raises(node_util.AbsentParametersError, message=msg):
            node_util.get_parameters(mock_node, filename, parameters_to_get,
                                     ensure=ensure)
    else:
        result = node_util.get_parameters(
            mock_node, filename, parameters_to_get, ensure=ensure)
        assert result == parameters
    mock_get.assert_called_once_with(
        mock_sftp.return_value.open.return_value.__enter__.return_value,
        parameters_to_get)
