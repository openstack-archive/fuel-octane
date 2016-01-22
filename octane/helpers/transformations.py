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

import argparse
import os
import re
import yaml

from distutils.version import StrictVersion
from octane import magic_consts


def get_parser():
    parser = argparse.ArgumentParser(description="Remove patch ports from "
                                                 "deployment configuration "
                                                 "of environment")
    parser.add_argument("dirname",
                        help="Name of directory that contains deployment "
                             "configuration of environment.")
    subparsers = parser.add_subparsers()

    parser_a = subparsers.add_parser("remove_patch_ports",
                                     help="Remove patch ports.")
    parser_a.set_defaults(action=remove_patch_ports)

    parser_b = subparsers.add_parser("remove_predefined_nets",
                                     help="Remove predefined networks.")
    parser_b.set_defaults(action=remove_predefined_nets)

    parser_c = subparsers.add_parser("remove_physical_ports",
                                     help="Remove physical ports from linux "
                                     "bridge.")
    parser_c.set_defaults(action=remove_physical_ports)

    parser_d = subparsers.add_parser("reset_gw_admin",
                                     help="Move gateway from external net to "
                                     "admin net.")
    parser_d.set_defaults(action=reset_gw_admin)

    return parser


def load_yaml_file(filename):
    with open(filename) as f:
        return yaml.safe_load(f)


def dump_yaml_file(dict_obj, filename):
    with open(filename, 'w') as f:
        yaml.dump(dict_obj, f, default_flow_style=False)


def get_actions(host_config):
    return host_config['network_scheme']['transformations']


def remove_patch_port(host_config, bridge_name):
    transformations = host_config['network_scheme']['transformations']
    for action in transformations:
        if (action['action'] == 'add-patch') and (
                bridge_name in action['bridges']):
            transformations.remove(action)
    return host_config


def remove_physical_port(host_config, bridge_name):
    transformations = host_config['network_scheme']['transformations']
    for action in transformations:
        if (action['action'] == 'add-port') and (
                action.get('bridge')) and (
                bridge_name == action['bridge']):
            action.pop('bridge')
    return host_config


def remove_patch_ports(host_config):
    for bridge_name in magic_consts.BRIDGES:
        host_config = remove_patch_port(host_config, bridge_name)
    return host_config


def remove_physical_ports(host_config):
    for bridge_name in magic_consts.BRIDGES:
        host_config = remove_physical_port(host_config, bridge_name)
    return host_config


def remove_predefined_nets(host_config):
    host_config["quantum_settings"]["predefined_networks"] = {}
    return host_config


def get_network_gw(data, network_name):
    for net in data['networks']:
        if net['name'] == network_name:
            return net.get('gateway')
    else:
        return None


def reset_gw_admin(host_config, gateway=None):
    if gateway:
        gw = gateway
    else:
        gw = host_config["master_ip"]
    endpoints = host_config["network_scheme"]["endpoints"]
    if endpoints["br-ex"].get("gateway"):
        endpoints["br-ex"]["gateway"] = 'none'
        endpoints["br-fw-admin"]["gateway"] = gw
    return host_config


def update_env_deployment_info(dirname, action):
    pattern = "^[-\w]+_\d+.yaml$"
    host_files = os.listdir(dirname)
    for filename in host_files:
        if re.match(pattern, filename):
            host_file = os.path.join(dirname, filename)
            host_config = load_yaml_file(host_file)
            host_config = action(host_config)
            dump_yaml_file(host_config, host_file)


def get_bridge_provider(actions, bridge):
    add_br_actions = [action for action in actions
                      if action.get("action") == "add-br"]
    providers = [action.get("provider", "lnx") for action in add_br_actions
                 if action.get("name") == bridge]
    if len(providers):
        return providers[-1]
    else:
        return 'lnx'


def get_admin_iface(actions):
    return 'br-fw-admin'


def get_patch_port_action(host_config, bridge):
    actions = get_actions(host_config)
    version = host_config.get('openstack_version')
    _, _, fuel_version = version.rpartition('-')
    provider = 'ovs'
    if StrictVersion(fuel_version) >= StrictVersion('6.1'):
        provider = get_bridge_provider(actions, bridge)
    for action in actions:
        if provider == 'ovs' and action.get('action') == 'add-patch':
            bridges = action.get('bridges', [])
            if bridge in bridges:
                return action, provider
        elif provider == 'lnx' and action.get('action') == 'add-port':
            if action.get('bridge') == bridge:
                return action, provider


def lnx_add_port(actions, bridge):
    for action in actions:
        if (action.get("action") == "add-port" and
                action.get("bridge") == bridge):
            port = action.get("name")
    if port:
        return ["brctl addif {0} {1}; ip link set up dev {1}"
                .format(bridge, port)]


def ovs_add_patch_ports(actions, bridge):
    for action in actions:
        if (action.get("action") == "add-patch" and
                bridge in action.get("bridges", [])):
            bridges = action.get("bridges", [])
            tags = action.get("tags", ["", ""])
            trunks = action.get("trunks", [])
    for tag in tags:
        if tag:
            tag = "tag={0}".format(str(tag))
    trunk_str = ",".join(trunks)
    if trunk_str:
        trunk_param = "trunks=[{0}]".format(trunk_str)
    if bridges:
        return ["ovs-vsctl add-port {0} {0}--{1} {3} {4}"
                "-- set interface {0}--{1} type=patch "
                "options:peer={1}--{0}"
                .format(bridges[0], bridges[1], tags[0], trunk_param),
                "ovs-vsctl add-port {1} {1}--{0} {3} {4}"
                "-- set interface {1}--{0} type=patch "
                "options:peer={0}--{1}"
                .format(bridges[0], bridges[1], tags[1], trunk_param)]


def remove_ports(host_config):
    actions = host_config['network_scheme']['transformations']
    for bridge_name in magic_consts.BRIDGES:
        provider = get_bridge_provider(actions, bridge_name)
        if provider == 'ovs':
            remove_patch_port(host_config, bridge_name)
        else:
            remove_physical_port(host_config, bridge_name)


def main():
    args = get_parser().parse_args()

    update_env_deployment_info(args.dirname, args.action)


if __name__ == "__main__":
    main()
