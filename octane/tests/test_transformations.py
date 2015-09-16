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
from octane.helpers import transformations


_host_config = {
    "openstack_version": "2015.1-7.0",
    "network_scheme": {
        "interfaces": {
            "eth0": {
                "L2": {
                    "vlan_splinters": "off"
                }
            },
            "eth1": {
                "L2": {
                    "vlan_splinters": "off"
                }
            },
            "eth2": {
                "L2": {
                    "vlan_splinters": "off"
                }
            },
            "eth3": {
                "L2": {
                    "vlan_splinters": "off"
                }
            },
            "eth4": {
                "L2": {
                    "vlan_splinters": "off"
                }
            },
            "eth5": {
                "L2": {
                    "vlan_splinters": "off"
                }
            },
            "eth6": {
                "L2": {
                    "vlan_splinters": "off"
                }
            },

        },
        "transformations": [
            {
                "action": "add-br",
                "name": "lnx-br0"
            },
            {
                "action": "add-port",
                "name": "eth5.390"
            },
            {
                "action": "add-port",
                "bridge": "lnx-br0",
                "name": "eth5.388"
            },
            {
                "action": "add-br",
                "name": "lnx-br1"
            },
            {
                "action": "add-bond",
                "interfaces": [
                    "eth1.400",
                    "eth0.400"
                ],
                "bridge": "lnx-br1",
                "name": "lnx-bond0",
                "properties": [
                    "bond_mode=active-backup"
                ]
            },
            {
                "action": "add-br",
                "name": "lnx-br2"
            },
            {
                "action": "add-port",
                "bridge": "lnx-br2",
                "name": "eth6"
            },
            {
                "action": "add-bond",
                "interfaces": [
                    "eth1.500",
                    "eth0.500"
                ],
                "name": "lnx-bond1",
                "properties": [
                    "bond_mode=active-backup"
                ]
            },
            {
                "action": "add-br",
                "name": "br-ovs-bond0"
            },
            {
                "action": "add-bond",
                "bridge": "br-ovs-bond0",
                "provider": "ovs",
                "interfaces": [
                    "eth1",
                    "eth0"
                ],
                "name": "ovs-bond0",
                "properties": [
                    "bond_mode=active-backup"
                ]
            },
            {
                "action": "add-br",
                "name": "br-ovs-bond1"
            },
            {
                "action": "add-bond",
                "bridge": "br-ovs-bond1",
                "interfaces": [
                    "eth3",
                    "eth2"
                ],
                "name": "ovs-bond1",
                "properties": [
                    "bond_mode=active-backup"
                ]
            },
            {
                "action": "add-br",
                "name": "br-ovs-bond2"
            },
            {
                "action": "add-bond",
                "bridge": "br-ovs-bond2",
                "interfaces": [
                    "eth5",
                    "eth4"
                ],
                "name": "ovs-bond2",
                "properties": [
                    "bond_mode=active-backup"
                ]
            },
            {
                "action": "add-br",
                "name": "br-mgmt"
            },
            {
                "action": "add-br",
                "name": "br-fw-admin"
            },
            {
                "action": "add-br",
                "name": "br-ex"
            },
            {
                "action": "add-br",
                "name": "br-iscsi-left"
            },
            {
                "action": "add-br",
                "name": "br-iscsi-right"
            },
            {
                "action": "add-br",
                "name": "br-swift"
            },
            {
                "action": "add-patch",
                "bridges": [
                    "br-ovs-bond0",
                    "br-mgmt"
                ],
                "tags": [
                    100,
                    0
                ]
            },
            {
                "action": "add-patch",
                "bridges": [
                    "br-ovs-bond0",
                    "br-fw-admin"
                ],
                "trunks": [
                    0
                ]
            },
            {
                "action": "add-patch",
                "bridges": [
                    "br-ovs-bond1",
                    "br-ex"
                ],
                "trunks": [
                    0
                ]
            },
            {
                "action": "add-patch",
                "bridges": [
                    "br-ovs-bond2",
                    "br-iscsi-left"
                ],
                "tags": [
                    102,
                    0
                ]
            },
            {
                "action": "add-patch",
                "bridges": [
                    "br-ovs-bond2",
                    "br-iscsi-right"
                ],
                "tags": [
                    103,
                    0
                ]
            },
            {
                "action": "add-patch",
                "bridges": [
                    "br-ovs-bond2",
                    "br-swift"
                ],
                "tags": [
                    113,
                    0
                ]
            },
            {
                "action": "add-br",
                "name": "br-prv"
            },
            {
                "action": "add-patch",
                "bridges": [
                    "br-ovs-bond1",
                    "br-prv"
                ]
            }
        ]
    }
}

_patch_port_action_br_ex = {
    'action': 'add-patch',
    'bridges': [
        'br-ovs-bond1',
        'br-ex'
    ],
    'trunks': [0]
}

_patch_port_action_br_ovs_bond1 = {
    "action": "add-bond",
    "bridge": "br-ovs-bond1",
    "interfaces": [
        "eth3",
        "eth2"
    ],
    "name": "ovs-bond1",
    "properties": [
        "bond_mode=active-backup"
    ]
}

_patch_port_action_lnx_br2 = {
    "action": "add-port",
    "bridge": "lnx-br2",
    "name": "eth6"
}

_patch_port_action_lnx_br0 = {
    "action": "add-port",
    "bridge": "lnx-br0",
    "name": "eth5.388"
}


def test_get_port_action(mocker):
    host_config = _host_config
    bridge = "br-ex"
    res = transformations.get_port_action(host_config, bridge)
    assert res == (_patch_port_action_br_ex, 'lnx')


def test_get_port_action_bridge_connected_directly_to_bond(mocker):
    host_config = _host_config
    bridge = "br-ovs-bond1"
    res = transformations.get_port_action(host_config, bridge)
    assert res == (_patch_port_action_br_ovs_bond1, 'lnx')


def test_get_port_action_bridge_connected_directly_to_iface(mocker):
    host_config = _host_config
    bridge = "lnx-br2"
    res = transformations.get_port_action(host_config, bridge)
    assert res == (_patch_port_action_lnx_br2, 'lnx')


def test_get_port_action_bridge_connected_directly_to_subiface(mocker):
    host_config = _host_config
    bridge = "lnx-br0"
    res = transformations.get_port_action(host_config, bridge)
    assert res == (_patch_port_action_lnx_br0, 'lnx')


def test_get_physical_bridges(mocker):
    host_config = _host_config
    res = list(transformations.get_physical_bridges(host_config))
    assert res == ['lnx-br0', 'lnx-br2', 'lnx-br1', 'br-ovs-bond0',
                   'br-ovs-bond1', 'br-ovs-bond2']
