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

import pytest

from octane.helpers import transformations as ts


def test_reset_gw_admin(mocker):
    host_config = DEPLOYMENT_INFO
    gateway = '10.10.10.10'

    res = ts.reset_gw_admin(host_config, gateway)

    assert res['network_scheme']['endpoints']['br-fw-admin']['gateway'] == \
        gateway


def test_get_network_gw(mocker):
    net_name = 'test_net'
    gateway = '10.10.10.10'
    data = {
        'networks': [
            {
                'name': net_name,
                'gateway': gateway
            }
        ]
    }

    res = ts.get_network_gw(data, net_name)

    assert res == gateway


def test_get_network_gw_no_gw(mocker):
    net_name = 'test_net'
    data = {
        'networks': [{
            'name': net_name,
        }]
    }

    res = ts.get_network_gw(data, net_name)

    assert res is None


def test_get_network_gw_no_net(mocker):
    net_name = 'test_net'
    data = {
        'networks': [{
            'name': 'another_test_net',
            'gateway': '10.10.10.10'
        }]
    }

    res = ts.get_network_gw(data, net_name)

    assert res is None


DEPLOYMENT_INFO = {
    'network_scheme': {
        'endpoints': {
            'br-ex': {'gateway': '172.16.0.1', },
            'br-fw-admin': {}
        }
    }
}

DEFAULT_OVS_ACTION = {
    'action': 'add-patch',
    'bridges': ['test-br']
}
DEFAULT_LNX_ACTION = {
    'action': 'add-port',
    'bridge': 'test-br'
}
OVS_ACTION = {
    'action': 'add-patch',
    'bridges': ['test-br'],
    'provider': 'ovs'
}
LNX_ACTION = {
    'action': 'add-port',
    'bridge': 'test-br',
    'provider': 'lnx'
}
ADD_LNX_BR_ACTION = {
    'action': 'add-br',
    'provider': 'lnx',
    'name': 'test-br'
}
ADD_OVS_BR_ACTION = {
    'action': 'add-br',
    'provider': 'ovs',
    'name': 'test-br'
}
HOST_CONFIG_6_0 = {
    'openstack_version': '2014.2-6.0',
    'network_scheme': {
        'transformations': [
            DEFAULT_LNX_ACTION,
            DEFAULT_OVS_ACTION
        ]
    }
}
HOST_CONFIG_6_1 = {
    'openstack_version': '2014.2.2-6.1',
    'network_scheme': {
        'transformations': [
            DEFAULT_LNX_ACTION,
        ]
    }
}
HOST_CONFIG_7_0 = {
    'openstack_version': '2015.1.0-7.0',
    'network_scheme': {
        'transformations': [
            OVS_ACTION,
            DEFAULT_OVS_ACTION,
            ADD_OVS_BR_ACTION
        ]
    }
}


@pytest.mark.parametrize('host_config,expected_action', [
    (HOST_CONFIG_6_0, DEFAULT_OVS_ACTION),
    (HOST_CONFIG_6_1, DEFAULT_LNX_ACTION),
    (HOST_CONFIG_7_0, OVS_ACTION)])
def test_patch_port_action(host_config, expected_action):
    bridge = 'test-br'

    res, _ = ts.get_patch_port_action(host_config, bridge)
    assert res == expected_action
