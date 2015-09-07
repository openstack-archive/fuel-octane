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

from octane.util import maintenance


def test_parse_crm_status():
    res = list(maintenance.parse_crm_status(CRM_STATUS_SAMPLE))
    assert res == CRM_STATUS_PARSE_RESULT

CRM_STATUS_SAMPLE = """
Last updated: Fri Jul 31 15:02:15 2015
Last change: Thu Jul 30 14:56:04 2015
Stack: corosync
Current DC: node-1 (1) - partition with quorum
Version: 1.1.12-561c4cf
1 Nodes configured
16 Resources configured


Online: [ node-1 ]

 Clone Set: clone_p_vrouter [p_vrouter]
     Started: [ node-1 ]
 vip__management	(ocf::fuel:ns_IPaddr2):	Started node-1 
 vip__public_vrouter	(ocf::fuel:ns_IPaddr2):	Started node-1 
 vip__management_vrouter	(ocf::fuel:ns_IPaddr2):	Started node-1 
 vip__public	(ocf::fuel:ns_IPaddr2):	Started node-1 
 Master/Slave Set: master_p_conntrackd [p_conntrackd]
     Masters: [ node-1 ]
 Clone Set: clone_p_haproxy [p_haproxy]
     Started: [ node-1 ]
 Clone Set: clone_p_dns [p_dns]
     Started: [ node-1 ]
 Clone Set: clone_p_mysql [p_mysql]
     Started: [ node-1 ]
 Master/Slave Set: master_p_rabbitmq-server [p_rabbitmq-server]
     Masters: [ node-1 ]
 Clone Set: clone_p_heat-engine [p_heat-engine]
     Started: [ node-1 ]
 Clone Set: clone_p_neutron-plugin-openvswitch-agent [p_neutron-plugin-openvswitch-agent]
     Started: [ node-1 ]
 Clone Set: clone_p_neutron-dhcp-agent [p_neutron-dhcp-agent]
     Started: [ node-1 ]
 Clone Set: clone_p_neutron-metadata-agent [p_neutron-metadata-agent]
     Started: [ node-1 ]
 Clone Set: clone_p_neutron-l3-agent [p_neutron-l3-agent]
     Started: [ node-1 ]
 Clone Set: clone_p_ntp [p_ntp]
     Started: [ node-1 ]
"""[1:]  # noqa
CRM_STATUS_PARSE_RESULT = [
    "p_vrouter",
    "p_heat-engine",
    "p_neutron-plugin-openvswitch-agent",
    "p_neutron-dhcp-agent",
    "p_neutron-metadata-agent",
    "p_neutron-l3-agent",
]
