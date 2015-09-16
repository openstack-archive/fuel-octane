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

from octane.util import maintenance
from octane.util import subprocess


def test_parse_crm_status():
    res = list(maintenance.parse_crm_status(CRM_STATUS_SAMPLE))
    assert res == CRM_STATUS_PARSE_RESULT


def test_get_crm_services():
    res = list(maintenance.get_crm_services(CRM_XML_SAMPLE))
    assert sorted(res) == CRM_XML_PARSE_RESULT


def test_stop_corosync_services(mocker, mock_ssh_call, mock_ssh_call_output,
                                mock_subprocess, node):
    get_one_controller = mocker.patch('octane.util.env.get_one_controller')
    get_one_controller.return_value = node

    get_crm_services = mocker.patch.object(maintenance, 'get_crm_services')
    get_crm_services.return_value = ['s1', 's2']

    mock_ssh_call.side_effect = \
        [subprocess.CalledProcessError(1, 'cmd'), None, None]

    mocker.patch('time.sleep')

    maintenance.stop_corosync_services('env')

    assert not mock_subprocess.called
    mock_ssh_call_output.assert_called_once_with(['crm_mon', '--as-xml'],
                                                 node=node)
    assert mock_ssh_call.call_args_list == [
        mock.call(['crm', 'resource', 'stop', 's1'], node=node),
        mock.call(['crm', 'resource', 'stop', 's1'], node=node),
        mock.call(['crm', 'resource', 'stop', 's2'], node=node),
    ]


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
CRM_XML_SAMPLE = """
<?xml version="1.0"?>
<crm_mon version="1.1.12">
    <summary>
        <last_update time="Tue Sep 15 16:40:20 2015" />
        <last_change time="Tue Sep 15 13:35:19 2015" user="" client="" origin="" />
        <stack type="corosync" />
        <current_dc present="true" version="1.1.12-561c4cf" name="node-3" id="3" with_quorum="true" />
        <nodes_configured number="1" expected_votes="unknown" />
        <resources_configured number="21" />
    </summary>
    <nodes>
        <node name="node-3" id="3" online="true" standby="false" standby_onfail="false" maintenance="false" pending="false" unclean="false" shutdown="false" expected_up="true" is_dc="true" resources_running="21" type="member" />
    </nodes>
    <resources>
        <clone id="clone_p_vrouter" multi_state="false" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_vrouter" resource_agent="ocf::fuel:ns_vrouter" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <resource id="vip__management" resource_agent="ocf::fuel:ns_IPaddr2" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
            <node name="node-3" id="3" cached="false"/>
        </resource>
        <resource id="vip__vrouter_pub" resource_agent="ocf::fuel:ns_IPaddr2" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
            <node name="node-3" id="3" cached="false"/>
        </resource>
        <resource id="vip__vrouter" resource_agent="ocf::fuel:ns_IPaddr2" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
            <node name="node-3" id="3" cached="false"/>
        </resource>
        <resource id="vip__public" resource_agent="ocf::fuel:ns_IPaddr2" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
            <node name="node-3" id="3" cached="false"/>
        </resource>
        <clone id="master_p_conntrackd" multi_state="true" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_conntrackd" resource_agent="ocf::fuel:ns_conntrackd" role="Master" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <clone id="clone_p_haproxy" multi_state="false" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_haproxy" resource_agent="ocf::fuel:ns_haproxy" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <clone id="clone_p_dns" multi_state="false" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_dns" resource_agent="ocf::fuel:ns_dns" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <clone id="master_p_rabbitmq-server" multi_state="true" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_rabbitmq-server" resource_agent="ocf::fuel:rabbitmq-server" role="Master" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <clone id="clone_p_mysql" multi_state="false" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_mysql" resource_agent="ocf::fuel:mysql-wss" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <resource id="p_ceilometer-agent-central" resource_agent="ocf::fuel:ceilometer-agent-central" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
            <node name="node-3" id="3" cached="false"/>
        </resource>
        <resource id="p_ceilometer-alarm-evaluator" resource_agent="ocf::fuel:ceilometer-alarm-evaluator" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
            <node name="node-3" id="3" cached="false"/>
        </resource>
        <clone id="clone_p_heat-engine" multi_state="false" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_heat-engine" resource_agent="ocf::fuel:heat-engine" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <clone id="clone_p_neutron-plugin-openvswitch-agent" multi_state="false" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_neutron-plugin-openvswitch-agent" resource_agent="ocf::fuel:ocf-neutron-ovs-agent" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <clone id="clone_p_neutron-dhcp-agent" multi_state="false" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_neutron-dhcp-agent" resource_agent="ocf::fuel:ocf-neutron-dhcp-agent" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <clone id="clone_p_neutron-metadata-agent" multi_state="false" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_neutron-metadata-agent" resource_agent="ocf::fuel:ocf-neutron-metadata-agent" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <clone id="clone_p_neutron-l3-agent" multi_state="false" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_neutron-l3-agent" resource_agent="ocf::fuel:ocf-neutron-l3-agent" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <clone id="clone_p_ntp" multi_state="false" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_ntp" resource_agent="ocf::fuel:ns_ntp" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="3" cached="false"/>
            </resource>
        </clone>
        <resource id="p_cinder-volume" resource_agent="ocf::fuel:cinder-volume" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
            <node name="node-3" id="3" cached="false"/>
        </resource>
        <group id="group__zabbix-server" number_resources="2" >
             <resource id="vip__zbx_vip_mgmt" resource_agent="ocf::fuel:ns_IPaddr2" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                 <node name="node-3" id="3" cached="false"/>
             </resource>
             <resource id="p_zabbix-server" resource_agent="ocf::fuel:zabbix-server" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                 <node name="node-3" id="3" cached="false"/>
             </resource>
        </group>
    </resources>
    <failures>
        <failure op_key="p_cinder-volume_monitor_20000" node="node-3" exitstatus="not running" exitcode="7" call="883" status="complete" last-rc-change="Tue Sep 15 08:29:56 2015" queued="0" exec="0" interval="20000" task="monitor" />
    </failures>
</crm_mon>
"""[1:]  # noqa
CRM_XML_PARSE_RESULT = [
    'clone_p_heat-engine',
    'clone_p_neutron-dhcp-agent',
    'clone_p_neutron-l3-agent',
    'clone_p_neutron-metadata-agent',
    'clone_p_neutron-plugin-openvswitch-agent',
    'clone_p_vrouter',
    'group__zabbix-server',
    'master_p_conntrackd',
    'master_p_rabbitmq-server',
    'p_ceilometer-agent-central',
    'p_ceilometer-alarm-evaluator',
    'p_cinder-volume',
]
