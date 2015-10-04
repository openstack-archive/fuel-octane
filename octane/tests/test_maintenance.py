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
from xml.etree import ElementTree

from octane.util import maintenance
from octane.util import subprocess


def test_get_crm_services():
    res = list(maintenance.get_crm_services(CRM_XML_SAMPLE))
    assert sorted(res) == CRM_XML_PARSE_RESULT


def test_resources_synced():
    resource_list = ["master_p_rabbitmq-server", "vip__management_old"]
    res = maintenance.is_resources_synced(resource_list, CRM_XML_STATUS_SAMPLE,
                                          False)
    assert res is False

    resource_list = ["master_p_rabbitmq-server", "vip__management_old"]
    res = maintenance.is_resources_synced(resource_list, CRM_XML_STATUS_SAMPLE,
                                          True)
    assert res is False

    resource_list = ["master_p_rabbitmq-server",
                     "p_ceilometer-alarm-evaluator"]
    res = maintenance.is_resources_synced(resource_list, CRM_XML_STATUS_SAMPLE,
                                          False)
    assert res is True

    resource_list = ["clone_p_neutron-metadata-agent", "vip__management_old",
                     "group__zabbix-server"]
    res = maintenance.is_resources_synced(resource_list, CRM_XML_STATUS_SAMPLE,
                                          True)
    assert res is True

    resource_list = ["test1", "vip__management_old"]
    res = maintenance.is_resources_synced(resource_list, CRM_XML_STATUS_SAMPLE,
                                          True)
    assert res is False

    resource_list = ["test1", "test2"]
    res = maintenance.is_resources_synced(resource_list, CRM_XML_STATUS_SAMPLE,
                                          False)
    assert res is True


def test_resources_status():
    data = ElementTree.fromstring(CRM_XML_STATUS_SAMPLE)
    resources = next(el for el in data if el.tag == 'resources')

    result = []
    for resource in resources:
        result.append(maintenance.is_resource_active(resource))
    assert result == [True, False, False, True, True]


def test_stop_corosync_services(mocker, mock_ssh_call, mock_ssh_call_output,
                                mock_subprocess, node):
    get_one_controller = mocker.patch('octane.util.env.get_one_controller')
    get_one_controller.return_value = node

    get_crm_services = mocker.patch.object(maintenance, 'get_crm_services')
    get_crm_services.return_value = ['s1', 's2']

    mock_ssh_call.side_effect = \
        [subprocess.CalledProcessError(1, 'cmd'), None, None]

    mocker.patch('time.sleep')

    wait_for_services = \
        mocker.patch('octane.util.maintenance.wait_for_corosync_services_sync')

    maintenance.stop_corosync_services('env')

    assert not mock_subprocess.called

    mock_ssh_call_output.assert_called_once_with(['cibadmin', '--query',
                                                  '--scope', 'resources'],
                                                 node=node)
    assert wait_for_services.call_args_list == [mock.call('env', False)]
    assert mock_ssh_call.call_args_list == [
        mock.call(['crm', 'resource', 'stop', 's1'], node=node),
        mock.call(['crm', 'resource', 'stop', 's1'], node=node),
        mock.call(['crm', 'resource', 'stop', 's2'], node=node),
    ]


def test_start_corosync_services(mocker, mock_ssh_call, mock_ssh_call_output,
                                 mock_subprocess, node):
    get_controllers = mocker.patch('octane.util.env.get_controllers')
    get_controllers.return_value = iter([node])
    get_crm_services = mocker.patch.object(maintenance, 'get_crm_services')
    get_crm_services.return_value = ['test_service1', 'test_service2']
    mock_ssh_call.side_effect = \
        [None, subprocess.CalledProcessError(1, 'cmd'), None]

    wait_for_services = \
        mocker.patch('octane.util.maintenance.wait_for_corosync_services_sync')

    maintenance.start_corosync_services('env')

    mock_ssh_call_output.assert_called_once_with(
        ['cibadmin', '--query', '--scope', 'resources'], node=node)

    assert wait_for_services.call_args_list == [mock.call('env', True)]
    assert mock_ssh_call.call_args_list == [
        mock.call(['crm', 'resource', 'start', 'test_service1'], node=node),
        mock.call(['crm', 'resource', 'start', 'test_service2'], node=node),
        mock.call(['crm', 'resource', 'start', 'test_service2'], node=node),
    ]


CRM_XML_SAMPLE = """
<resources>
  <clone id="clone_p_vrouter">
    <meta_attributes id="clone_p_vrouter-meta_attributes">
      <nvpair id="clone_p_vrouter-meta_attributes-interleave" name="interleave" value="true"/>
    </meta_attributes>
    <primitive class="ocf" id="p_vrouter" provider="fuel" type="ns_vrouter">
      <operations>
        <op id="p_vrouter-monitor-30" interval="30" name="monitor" timeout="60"/>
        <op id="p_vrouter-start-0" interval="0" name="start" timeout="30"/>
        <op id="p_vrouter-stop-0" interval="0" name="stop" timeout="60"/>
      </operations>
      <instance_attributes id="p_vrouter-instance_attributes">
        <nvpair id="p_vrouter-instance_attributes-ns" name="ns" value="vrouter"/>
        <nvpair id="p_vrouter-instance_attributes-other_networks" name="other_networks" value="192.168.2.0/24 10.108.0.0/24 192.168.113.0/24 192.168.0.0/24 192.168.3.0/24 10.108.2.0/24"/>
      </instance_attributes>
      <meta_attributes id="p_vrouter-meta_attributes">
        <nvpair id="p_vrouter-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
        <nvpair id="p_vrouter-meta_attributes-failure-timeout" name="failure-timeout" value="120"/>
      </meta_attributes>
    </primitive>
  </clone>
  <primitive class="ocf" id="vip__management" provider="fuel" type="ns_IPaddr2">
    <operations>
      <op id="vip__management-monitor-5" interval="5" name="monitor" timeout="20"/>
      <op id="vip__management-start-0" interval="0" name="start" timeout="30"/>
      <op id="vip__management-stop-0" interval="0" name="stop" timeout="30"/>
    </operations>
    <instance_attributes id="vip__management-instance_attributes">
      <nvpair id="vip__management-instance_attributes-bridge" name="bridge" value="br-mgmt"/>
      <nvpair id="vip__management-instance_attributes-base_veth" name="base_veth" value="v_management"/>
      <nvpair id="vip__management-instance_attributes-ns_veth" name="ns_veth" value="b_management"/>
      <nvpair id="vip__management-instance_attributes-ip" name="ip" value="192.168.0.2"/>
      <nvpair id="vip__management-instance_attributes-iflabel" name="iflabel" value="ka"/>
      <nvpair id="vip__management-instance_attributes-cidr_netmask" name="cidr_netmask" value="24"/>
      <nvpair id="vip__management-instance_attributes-ns" name="ns" value="haproxy"/>
      <nvpair id="vip__management-instance_attributes-gateway_metric" name="gateway_metric" value="0"/>
    </instance_attributes>
    <meta_attributes id="vip__management-meta_attributes">
      <nvpair id="vip__management-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
      <nvpair id="vip__management-meta_attributes-failure-timeout" name="failure-timeout" value="60"/>
      <nvpair id="vip__management-meta_attributes-resource-stickiness" name="resource-stickiness" value="1"/>
    </meta_attributes>
  </primitive>
  <primitive class="ocf" id="vip__vrouter_pub" provider="fuel" type="ns_IPaddr2">
    <operations>
      <op id="vip__vrouter_pub-monitor-5" interval="5" name="monitor" timeout="20"/>
      <op id="vip__vrouter_pub-start-0" interval="0" name="start" timeout="30"/>
      <op id="vip__vrouter_pub-stop-0" interval="0" name="stop" timeout="30"/>
    </operations>
    <instance_attributes id="vip__vrouter_pub-instance_attributes">
      <nvpair id="vip__vrouter_pub-instance_attributes-bridge" name="bridge" value="br-ex"/>
      <nvpair id="vip__vrouter_pub-instance_attributes-base_veth" name="base_veth" value="v_vrouter_pub"/>
      <nvpair id="vip__vrouter_pub-instance_attributes-ns_veth" name="ns_veth" value="b_vrouter_pub"/>
      <nvpair id="vip__vrouter_pub-instance_attributes-ip" name="ip" value="10.108.2.6"/>
      <nvpair id="vip__vrouter_pub-instance_attributes-iflabel" name="iflabel" value="ka"/>
      <nvpair id="vip__vrouter_pub-instance_attributes-cidr_netmask" name="cidr_netmask" value="24"/>
      <nvpair id="vip__vrouter_pub-instance_attributes-ns" name="ns" value="vrouter"/>
      <nvpair id="vip__vrouter_pub-instance_attributes-gateway_metric" name="gateway_metric" value="0"/>
      <nvpair id="vip__vrouter_pub-instance_attributes-ns_iptables_start_rules" name="ns_iptables_start_rules" value="iptables -t nat -A POSTROUTING -o b_vrouter_pub -j MASQUERADE"/>
      <nvpair id="vip__vrouter_pub-instance_attributes-ns_iptables_stop_rules" name="ns_iptables_stop_rules" value="iptables -t nat -D POSTROUTING -o b_vrouter_pub -j MASQUERADE"/>
    </instance_attributes>
    <meta_attributes id="vip__vrouter_pub-meta_attributes">
      <nvpair id="vip__vrouter_pub-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
      <nvpair id="vip__vrouter_pub-meta_attributes-failure-timeout" name="failure-timeout" value="60"/>
      <nvpair id="vip__vrouter_pub-meta_attributes-resource-stickiness" name="resource-stickiness" value="1"/>
    </meta_attributes>
  </primitive>
  <primitive class="ocf" id="vip__vrouter" provider="fuel" type="ns_IPaddr2">
    <operations>
      <op id="vip__vrouter-monitor-5" interval="5" name="monitor" timeout="20"/>
      <op id="vip__vrouter-start-0" interval="0" name="start" timeout="30"/>
      <op id="vip__vrouter-stop-0" interval="0" name="stop" timeout="30"/>
    </operations>
    <instance_attributes id="vip__vrouter-instance_attributes">
      <nvpair id="vip__vrouter-instance_attributes-bridge" name="bridge" value="br-mgmt"/>
      <nvpair id="vip__vrouter-instance_attributes-base_veth" name="base_veth" value="v_vrouter"/>
      <nvpair id="vip__vrouter-instance_attributes-ns_veth" name="ns_veth" value="b_vrouter"/>
      <nvpair id="vip__vrouter-instance_attributes-ip" name="ip" value="192.168.0.1"/>
      <nvpair id="vip__vrouter-instance_attributes-iflabel" name="iflabel" value="ka"/>
      <nvpair id="vip__vrouter-instance_attributes-cidr_netmask" name="cidr_netmask" value="24"/>
      <nvpair id="vip__vrouter-instance_attributes-ns" name="ns" value="vrouter"/>
      <nvpair id="vip__vrouter-instance_attributes-gateway_metric" name="gateway_metric" value="0"/>
    </instance_attributes>
    <meta_attributes id="vip__vrouter-meta_attributes">
      <nvpair id="vip__vrouter-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
      <nvpair id="vip__vrouter-meta_attributes-failure-timeout" name="failure-timeout" value="60"/>
      <nvpair id="vip__vrouter-meta_attributes-resource-stickiness" name="resource-stickiness" value="1"/>
    </meta_attributes>
  </primitive>
  <primitive class="ocf" id="vip__public" provider="fuel" type="ns_IPaddr2">
    <operations>
      <op id="vip__public-monitor-5" interval="5" name="monitor" timeout="20"/>
      <op id="vip__public-start-0" interval="0" name="start" timeout="30"/>
      <op id="vip__public-stop-0" interval="0" name="stop" timeout="30"/>
    </operations>
    <instance_attributes id="vip__public-instance_attributes">
      <nvpair id="vip__public-instance_attributes-bridge" name="bridge" value="br-ex"/>
      <nvpair id="vip__public-instance_attributes-base_veth" name="base_veth" value="v_public"/>
      <nvpair id="vip__public-instance_attributes-ns_veth" name="ns_veth" value="b_public"/>
      <nvpair id="vip__public-instance_attributes-ip" name="ip" value="10.108.2.2"/>
      <nvpair id="vip__public-instance_attributes-iflabel" name="iflabel" value="ka"/>
      <nvpair id="vip__public-instance_attributes-cidr_netmask" name="cidr_netmask" value="24"/>
      <nvpair id="vip__public-instance_attributes-ns" name="ns" value="haproxy"/>
      <nvpair id="vip__public-instance_attributes-gateway_metric" name="gateway_metric" value="10"/>
    </instance_attributes>
    <meta_attributes id="vip__public-meta_attributes">
      <nvpair id="vip__public-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
      <nvpair id="vip__public-meta_attributes-failure-timeout" name="failure-timeout" value="60"/>
      <nvpair id="vip__public-meta_attributes-resource-stickiness" name="resource-stickiness" value="1"/>
    </meta_attributes>
  </primitive>
  <master id="master_p_conntrackd">
    <meta_attributes id="master_p_conntrackd-meta_attributes">
      <nvpair id="master_p_conntrackd-meta_attributes-notify" name="notify" value="true"/>
      <nvpair id="master_p_conntrackd-meta_attributes-ordered" name="ordered" value="false"/>
      <nvpair id="master_p_conntrackd-meta_attributes-interleave" name="interleave" value="true"/>
      <nvpair id="master_p_conntrackd-meta_attributes-clone-node-max" name="clone-node-max" value="1"/>
      <nvpair id="master_p_conntrackd-meta_attributes-master-max" name="master-max" value="1"/>
      <nvpair id="master_p_conntrackd-meta_attributes-master-node-max" name="master-node-max" value="1"/>
    </meta_attributes>
    <primitive class="ocf" id="p_conntrackd" provider="fuel" type="ns_conntrackd">
      <operations>
        <op id="p_conntrackd-monitor-30" interval="30" name="monitor" timeout="60"/>
        <op id="p_conntrackd-monitor-27" interval="27" name="monitor" role="Master" timeout="60"/>
      </operations>
      <meta_attributes id="p_conntrackd-meta_attributes">
        <nvpair id="p_conntrackd-meta_attributes-migration-threshold" name="migration-threshold" value="INFINITY"/>
        <nvpair id="p_conntrackd-meta_attributes-failure-timeout" name="failure-timeout" value="180s"/>
      </meta_attributes>
    </primitive>
  </master>
  <clone id="clone_p_haproxy">
    <meta_attributes id="clone_p_haproxy-meta_attributes">
      <nvpair id="clone_p_haproxy-meta_attributes-interleave" name="interleave" value="true"/>
    </meta_attributes>
    <primitive class="ocf" id="p_haproxy" provider="fuel" type="ns_haproxy">
      <operations>
        <op id="p_haproxy-monitor-30" interval="30" name="monitor" timeout="60"/>
        <op id="p_haproxy-start-0" interval="0" name="start" timeout="60"/>
        <op id="p_haproxy-stop-0" interval="0" name="stop" timeout="60"/>
      </operations>
      <instance_attributes id="p_haproxy-instance_attributes">
        <nvpair id="p_haproxy-instance_attributes-ns" name="ns" value="haproxy"/>
        <nvpair id="p_haproxy-instance_attributes-debug" name="debug" value="true"/>
        <nvpair id="p_haproxy-instance_attributes-other_networks" name="other_networks" value="192.168.2.0/24 10.108.0.0/24 10.108.2.0/24 192.168.0.0/24 192.168.3.0/24 192.168.113.0/24"/>
      </instance_attributes>
      <meta_attributes id="p_haproxy-meta_attributes">
        <nvpair id="p_haproxy-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
        <nvpair id="p_haproxy-meta_attributes-failure-timeout" name="failure-timeout" value="120"/>
      </meta_attributes>
    </primitive>
  </clone>
  <master id="master_p_rabbitmq-server">
    <meta_attributes id="master_p_rabbitmq-server-meta_attributes">
      <nvpair id="master_p_rabbitmq-server-meta_attributes-notify" name="notify" value="true"/>
      <nvpair id="master_p_rabbitmq-server-meta_attributes-ordered" name="ordered" value="false"/>
      <nvpair id="master_p_rabbitmq-server-meta_attributes-interleave" name="interleave" value="true"/>
      <nvpair id="master_p_rabbitmq-server-meta_attributes-master-max" name="master-max" value="1"/>
      <nvpair id="master_p_rabbitmq-server-meta_attributes-master-node-max" name="master-node-max" value="1"/>
    </meta_attributes>
    <primitive class="ocf" id="p_rabbitmq-server" provider="fuel" type="rabbitmq-server">
      <operations>
        <op id="p_rabbitmq-server-monitor-30" interval="30" name="monitor" timeout="180"/>
        <op id="p_rabbitmq-server-monitor-27" interval="27" name="monitor" role="Master" timeout="180"/>
        <op id="p_rabbitmq-server-monitor-103" interval="103" name="monitor" role="Slave" timeout="180">
          <instance_attributes id="p_rabbitmq-server-monitor-103-instance_attributes">
            <nvpair id="p_rabbitmq-server-monitor-103-instance_attributes-OCF_CHECK_LEVEL" name="OCF_CHECK_LEVEL" value="30"/>
          </instance_attributes>
        </op>
        <op id="p_rabbitmq-server-start-0" interval="0" name="start" timeout="360"/>
        <op id="p_rabbitmq-server-stop-0" interval="0" name="stop" timeout="120"/>
        <op id="p_rabbitmq-server-promote-0" interval="0" name="promote" timeout="120"/>
        <op id="p_rabbitmq-server-demote-0" interval="0" name="demote" timeout="120"/>
        <op id="p_rabbitmq-server-notify-0" interval="0" name="notify" timeout="180"/>
      </operations>
      <instance_attributes id="p_rabbitmq-server-instance_attributes">
        <nvpair id="p_rabbitmq-server-instance_attributes-node_port" name="node_port" value="5673"/>
        <nvpair id="p_rabbitmq-server-instance_attributes-debug" name="debug" value="true"/>
        <nvpair id="p_rabbitmq-server-instance_attributes-command_timeout" name="command_timeout" value="--signal=KILL"/>
        <nvpair id="p_rabbitmq-server-instance_attributes-erlang_cookie" name="erlang_cookie" value="EOKOWXQREETZSHFNTPEY"/>
        <nvpair id="p_rabbitmq-server-instance_attributes-admin_user" name="admin_user" value="nova"/>
        <nvpair id="p_rabbitmq-server-instance_attributes-admin_password" name="admin_password" value="YsYDuGb2"/>
      </instance_attributes>
      <meta_attributes id="p_rabbitmq-server-meta_attributes">
        <nvpair id="p_rabbitmq-server-meta_attributes-migration-threshold" name="migration-threshold" value="INFINITY"/>
        <nvpair id="p_rabbitmq-server-meta_attributes-failure-timeout" name="failure-timeout" value="360s"/>
      </meta_attributes>
    </primitive>
  </master>
  <clone id="clone_p_mysql">
    <primitive class="ocf" id="p_mysql" provider="fuel" type="mysql-wss">
      <operations>
        <op id="p_mysql-monitor-60" interval="60" name="monitor" timeout="55"/>
        <op id="p_mysql-start-0" interval="0" name="start" timeout="300"/>
        <op id="p_mysql-stop-0" interval="0" name="stop" timeout="120"/>
      </operations>
      <instance_attributes id="p_mysql-instance_attributes">
        <nvpair id="p_mysql-instance_attributes-test_user" name="test_user" value="wsrep_sst"/>
        <nvpair id="p_mysql-instance_attributes-test_passwd" name="test_passwd" value="RnxYbSsL"/>
        <nvpair id="p_mysql-instance_attributes-socket" name="socket" value="/var/run/mysqld/mysqld.sock"/>
      </instance_attributes>
    </primitive>
  </clone>
  <clone id="clone_p_dns">
    <meta_attributes id="clone_p_dns-meta_attributes">
      <nvpair id="clone_p_dns-meta_attributes-interleave" name="interleave" value="true"/>
    </meta_attributes>
    <primitive class="ocf" id="p_dns" provider="fuel" type="ns_dns">
      <operations>
        <op id="p_dns-monitor-20" interval="20" name="monitor" timeout="10"/>
        <op id="p_dns-start-0" interval="0" name="start" timeout="30"/>
        <op id="p_dns-stop-0" interval="0" name="stop" timeout="30"/>
      </operations>
      <instance_attributes id="p_dns-instance_attributes">
        <nvpair id="p_dns-instance_attributes-ns" name="ns" value="vrouter"/>
      </instance_attributes>
      <meta_attributes id="p_dns-meta_attributes">
        <nvpair id="p_dns-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
        <nvpair id="p_dns-meta_attributes-failure-timeout" name="failure-timeout" value="120"/>
      </meta_attributes>
    </primitive>
  </clone>
  <primitive class="ocf" id="p_ceilometer-agent-central" provider="fuel" type="ceilometer-agent-central">
    <operations>
      <op id="p_ceilometer-agent-central-monitor-20" interval="20" name="monitor" timeout="30"/>
      <op id="p_ceilometer-agent-central-start-0" interval="0" name="start" timeout="360"/>
      <op id="p_ceilometer-agent-central-stop-0" interval="0" name="stop" timeout="360"/>
    </operations>
    <instance_attributes id="p_ceilometer-agent-central-instance_attributes">
      <nvpair id="p_ceilometer-agent-central-instance_attributes-user" name="user" value="ceilometer"/>
    </instance_attributes>
    <meta_attributes id="p_ceilometer-agent-central-meta_attributes">
      <nvpair id="p_ceilometer-agent-central-meta_attributes-resource-stickiness" name="resource-stickiness" value="1"/>
      <nvpair id="p_ceilometer-agent-central-meta_attributes-target-role" name="target-role" value="Stopped"/>
    </meta_attributes>
  </primitive>
  <primitive class="ocf" id="p_ceilometer-alarm-evaluator" provider="fuel" type="ceilometer-alarm-evaluator">
    <operations>
      <op id="p_ceilometer-alarm-evaluator-monitor-20" interval="20" name="monitor" timeout="30"/>
      <op id="p_ceilometer-alarm-evaluator-start-0" interval="0" name="start" timeout="360"/>
      <op id="p_ceilometer-alarm-evaluator-stop-0" interval="0" name="stop" timeout="360"/>
    </operations>
    <instance_attributes id="p_ceilometer-alarm-evaluator-instance_attributes">
      <nvpair id="p_ceilometer-alarm-evaluator-instance_attributes-user" name="user" value="ceilometer"/>
    </instance_attributes>
    <meta_attributes id="p_ceilometer-alarm-evaluator-meta_attributes">
      <nvpair id="p_ceilometer-alarm-evaluator-meta_attributes-resource-stickiness" name="resource-stickiness" value="1"/>
      <nvpair id="p_ceilometer-alarm-evaluator-meta_attributes-target-role" name="target-role" value="Stopped"/>
    </meta_attributes>
  </primitive>
  <clone id="clone_p_neutron-plugin-openvswitch-agent">
    <meta_attributes id="clone_p_neutron-plugin-openvswitch-agent-meta_attributes">
      <nvpair id="clone_p_neutron-plugin-openvswitch-agent-meta_attributes-interleave" name="interleave" value="true"/>
      <nvpair id="clone_p_neutron-plugin-openvswitch-agent-meta_attributes-target-role" name="target-role" value="Stopped"/>
    </meta_attributes>
    <primitive class="ocf" id="p_neutron-plugin-openvswitch-agent" provider="fuel" type="ocf-neutron-ovs-agent">
      <operations>
        <op id="p_neutron-plugin-openvswitch-agent-monitor-20" interval="20" name="monitor" timeout="10"/>
        <op id="p_neutron-plugin-openvswitch-agent-start-0" interval="0" name="start" timeout="80"/>
        <op id="p_neutron-plugin-openvswitch-agent-stop-0" interval="0" name="stop" timeout="80"/>
      </operations>
      <instance_attributes id="p_neutron-plugin-openvswitch-agent-instance_attributes">
        <nvpair id="p_neutron-plugin-openvswitch-agent-instance_attributes-plugin_config" name="plugin_config" value="/etc/neutron/plugin.ini"/>
      </instance_attributes>
    </primitive>
  </clone>
  <clone id="clone_p_neutron-dhcp-agent">
    <meta_attributes id="clone_p_neutron-dhcp-agent-meta_attributes">
      <nvpair id="clone_p_neutron-dhcp-agent-meta_attributes-interleave" name="interleave" value="true"/>
      <nvpair id="clone_p_neutron-dhcp-agent-meta_attributes-target-role" name="target-role" value="Stopped"/>
    </meta_attributes>
    <primitive class="ocf" id="p_neutron-dhcp-agent" provider="fuel" type="ocf-neutron-dhcp-agent">
      <operations>
        <op id="p_neutron-dhcp-agent-monitor-20" interval="20" name="monitor" timeout="10"/>
        <op id="p_neutron-dhcp-agent-start-0" interval="0" name="start" timeout="60"/>
        <op id="p_neutron-dhcp-agent-stop-0" interval="0" name="stop" timeout="60"/>
      </operations>
      <instance_attributes id="p_neutron-dhcp-agent-instance_attributes">
        <nvpair id="p_neutron-dhcp-agent-instance_attributes-plugin_config" name="plugin_config" value="/etc/neutron/dhcp_agent.ini"/>
        <nvpair id="p_neutron-dhcp-agent-instance_attributes-remove_artifacts_on_stop_start" name="remove_artifacts_on_stop_start" value="true"/>
      </instance_attributes>
    </primitive>
  </clone>
  <clone id="clone_p_neutron-metadata-agent">
    <meta_attributes id="clone_p_neutron-metadata-agent-meta_attributes">
      <nvpair id="clone_p_neutron-metadata-agent-meta_attributes-interleave" name="interleave" value="true"/>
      <nvpair id="clone_p_neutron-metadata-agent-meta_attributes-target-role" name="target-role" value="Stopped"/>
    </meta_attributes>
    <primitive class="ocf" id="p_neutron-metadata-agent" provider="fuel" type="ocf-neutron-metadata-agent">
      <operations>
        <op id="p_neutron-metadata-agent-monitor-60" interval="60" name="monitor" timeout="10"/>
        <op id="p_neutron-metadata-agent-start-0" interval="0" name="start" timeout="30"/>
        <op id="p_neutron-metadata-agent-stop-0" interval="0" name="stop" timeout="30"/>
      </operations>
    </primitive>
  </clone>
  <clone id="clone_p_neutron-l3-agent">
    <meta_attributes id="clone_p_neutron-l3-agent-meta_attributes">
      <nvpair id="clone_p_neutron-l3-agent-meta_attributes-interleave" name="interleave" value="true"/>
      <nvpair id="clone_p_neutron-l3-agent-meta_attributes-target-role" name="target-role" value="Stopped"/>
    </meta_attributes>
    <primitive class="ocf" id="p_neutron-l3-agent" provider="fuel" type="ocf-neutron-l3-agent">
      <operations>
        <op id="p_neutron-l3-agent-monitor-20" interval="20" name="monitor" timeout="10"/>
        <op id="p_neutron-l3-agent-start-0" interval="0" name="start" timeout="60"/>
        <op id="p_neutron-l3-agent-stop-0" interval="0" name="stop" timeout="60"/>
      </operations>
      <instance_attributes id="p_neutron-l3-agent-instance_attributes">
        <nvpair id="p_neutron-l3-agent-instance_attributes-plugin_config" name="plugin_config" value="/etc/neutron/l3_agent.ini"/>
        <nvpair id="p_neutron-l3-agent-instance_attributes-remove_artifacts_on_stop_start" name="remove_artifacts_on_stop_start" value="true"/>
      </instance_attributes>
    </primitive>
  </clone>
  <clone id="clone_p_heat-engine">
    <meta_attributes id="clone_p_heat-engine-meta_attributes">
      <nvpair id="clone_p_heat-engine-meta_attributes-interleave" name="interleave" value="true"/>
      <nvpair id="clone_p_heat-engine-meta_attributes-target-role" name="target-role" value="Stopped"/>
    </meta_attributes>
    <primitive class="ocf" id="p_heat-engine" provider="fuel" type="heat-engine">
      <operations>
        <op id="p_heat-engine-monitor-20" interval="20" name="monitor" timeout="30"/>
        <op id="p_heat-engine-start-0" interval="0" name="start" timeout="60"/>
        <op id="p_heat-engine-stop-0" interval="0" name="stop" timeout="60"/>
      </operations>
      <meta_attributes id="p_heat-engine-meta_attributes">
        <nvpair id="p_heat-engine-meta_attributes-resource-stickiness" name="resource-stickiness" value="1"/>
        <nvpair id="p_heat-engine-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
      </meta_attributes>
    </primitive>
  </clone>
  <clone id="clone_p_ntp">
    <meta_attributes id="clone_p_ntp-meta_attributes">
      <nvpair id="clone_p_ntp-meta_attributes-interleave" name="interleave" value="true"/>
    </meta_attributes>
    <primitive class="ocf" id="p_ntp" provider="fuel" type="ns_ntp">
      <operations>
        <op id="p_ntp-monitor-20" interval="20" name="monitor" timeout="10"/>
        <op id="p_ntp-start-0" interval="0" name="start" timeout="30"/>
        <op id="p_ntp-stop-0" interval="0" name="stop" timeout="30"/>
      </operations>
      <instance_attributes id="p_ntp-instance_attributes">
        <nvpair id="p_ntp-instance_attributes-ns" name="ns" value="vrouter"/>
      </instance_attributes>
      <meta_attributes id="p_ntp-meta_attributes">
        <nvpair id="p_ntp-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
        <nvpair id="p_ntp-meta_attributes-failure-timeout" name="failure-timeout" value="120"/>
      </meta_attributes>
    </primitive>
  </clone>
  <group id="group__zabbix-server">
    <primitive class="ocf" id="vip__zbx_vip_mgmt" provider="fuel" type="ns_IPaddr2">
      <operations>
        <op id="vip__zbx_vip_mgmt-monitor-5" interval="5" name="monitor" timeout="20"/>
        <op id="vip__zbx_vip_mgmt-start-0" interval="0" name="start" timeout="30"/>
        <op id="vip__zbx_vip_mgmt-stop-0" interval="0" name="stop" timeout="30"/>
      </operations>
      <instance_attributes id="vip__zbx_vip_mgmt-instance_attributes">
        <nvpair id="vip__zbx_vip_mgmt-instance_attributes-bridge" name="bridge" value="br-mgmt"/>
        <nvpair id="vip__zbx_vip_mgmt-instance_attributes-base_veth" name="base_veth" value="v_zbx_vip_mgmt"/>
        <nvpair id="vip__zbx_vip_mgmt-instance_attributes-ns_veth" name="ns_veth" value="b_zbx_vip_mgmt"/>
        <nvpair id="vip__zbx_vip_mgmt-instance_attributes-ip" name="ip" value="192.168.0.8"/>
        <nvpair id="vip__zbx_vip_mgmt-instance_attributes-iflabel" name="iflabel" value="ka"/>
        <nvpair id="vip__zbx_vip_mgmt-instance_attributes-cidr_netmask" name="cidr_netmask" value="24"/>
        <nvpair id="vip__zbx_vip_mgmt-instance_attributes-ns" name="ns" value="haproxy"/>
        <nvpair id="vip__zbx_vip_mgmt-instance_attributes-gateway_metric" name="gateway_metric" value="0"/>
      </instance_attributes>
      <meta_attributes id="vip__zbx_vip_mgmt-meta_attributes">
        <nvpair id="vip__zbx_vip_mgmt-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
        <nvpair id="vip__zbx_vip_mgmt-meta_attributes-failure-timeout" name="failure-timeout" value="60"/>
        <nvpair id="vip__zbx_vip_mgmt-meta_attributes-resource-stickiness" name="resource-stickiness" value="1"/>
      </meta_attributes>
    </primitive>
    <primitive class="ocf" id="p_zabbix-server" provider="fuel" type="zabbix-server">
      <operations>
        <op id="p_zabbix-server-monitor-5s" interval="5s" name="monitor" timeout="30s"/>
        <op id="p_zabbix-server-start-0" interval="0" name="start" timeout="30s"/>
      </operations>
      <meta_attributes id="p_zabbix-server-meta_attributes">
        <nvpair id="p_zabbix-server-meta_attributes-migration-threshold" name="migration-threshold" value="3"/>
        <nvpair id="p_zabbix-server-meta_attributes-failure-timeout" name="failure-timeout" value="120"/>
      </meta_attributes>
    </primitive>
    <meta_attributes id="group__zabbix-server-meta_attributes">
      <nvpair id="group__zabbix-server-meta_attributes-target-role" name="target-role" value="Stopped"/>
    </meta_attributes>
  </group>
</resources>
"""[1:]  # noqa
CRM_XML_PARSE_RESULT = [
    'clone_p_heat-engine',
    'clone_p_neutron-dhcp-agent',
    'clone_p_neutron-l3-agent',
    'clone_p_neutron-metadata-agent',
    'clone_p_neutron-plugin-openvswitch-agent',
    'group__zabbix-server',
    'p_ceilometer-agent-central',
    'p_ceilometer-alarm-evaluator',
]
CRM_XML_STATUS_SAMPLE = """
<crm_mon version="1.1.12">
    <resources>
        <resource id="vip__management_old" resource_agent="ocf::mirantis:ns_IPaddr2" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
            <node name="node-2" id="node-2" cached="false"/>
        </resource>
        <resource id="p_ceilometer-alarm-evaluator" resource_agent="ocf::mirantis:ceilometer-alarm-evaluator" role="Started" active="false" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="0" />
        <clone id="master_p_rabbitmq-server" multi_state="true" unique="false" managed="true" failed="false" failure_ignored="false" >
            <resource id="p_rabbitmq-server" resource_agent="ocf::mirantis:rabbitmq-server" role="Master" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-3" id="node-3" cached="false"/>
            </resource>
            <resource id="p_rabbitmq-server" resource_agent="ocf::mirantis:rabbitmq-server" role="Slave" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                <node name="node-2" id="node-2" cached="false"/>
            </resource>
            <resource id="p_rabbitmq-server" resource_agent="ocf::mirantis:rabbitmq-server" role="Stopped" active="false" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="0" />
        </clone>
        <clone id="clone_p_neutron-metadata-agent" >
            <resource id="p_neutron-metadata-agent" resource_agent="ocf::mirantis:neutron-agent-metadata" active="true" >
                <node name="node-3" id="node-3" cached="false"/>
            </resource>
            <resource id="p_neutron-metadata-agent" resource_agent="ocf::mirantis:neutron-agent-metadata" active="true" >
                <node name="node-2" id="node-2" cached="false"/>
            </resource>
            <resource id="p_neutron-metadata-agent" resource_agent="ocf::mirantis:neutron-agent-metadata" active="true" >
                <node name="node-5" id="node-5" cached="false"/>
            </resource>
        </clone>
        <group id="group__zabbix-server" number_resources="2" >
             <resource id="vip__zbx_vip_mgmt" resource_agent="ocf::fuel:ns_IPaddr2" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                 <node name="node-6" id="6" cached="false"/>
             </resource>
             <resource id="p_zabbix-server" resource_agent="ocf::fuel:zabbix-server" role="Started" active="true" orphaned="false" managed="true" failed="false" failure_ignored="false" nodes_running_on="1" >
                 <node name="node-6" id="6" cached="false"/>
             </resource>
        </group>
    </resources>
</crm_mon>
"""[1:]  # noqa
