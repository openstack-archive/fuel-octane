import yaml
import os
import re
import argparse


BRIDGES = ('br-ex', 'br-mgmt')


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

    return parser


def load_yaml_file(filename):
    with open(filename) as f:
        return yaml.safe_load(f)


def dump_yaml_file(dict_obj, filename):
    with open(filename, 'w') as f:
        yaml.dump(dict_obj, f, default_flow_style=False)


def remove_patch_port(host_config, bridge_name):
    transformations = host_config['network_scheme']['transformations']
    for action in transformations:
        if (action['action'] == 'add-patch') and (bridge_name
                in action['bridges']):
            transformations.remove(action)
    return host_config


def remove_patch_ports(host_config):
    for bridge_name in BRIDGES:
        host_config = remove_patch_port(host_config, bridge_name)
    return host_config


def remove_predefined_nets(host_config):
    host_config["quantum_settings"]["predefined_networks"] = {}
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


def patch_port_params(host_file, bridge_name):
    host_config = load_yaml_file(host_file)
    transformations = host_config['network_scheme']['transformations']
    patches = [action for action in transformations
               if (action['action'] == 'add-patch')
               and (bridge_name in action['bridges'])]
    return([(patch['bridges'], patch['trunks']) for patch in patches])


def main():
    args = get_parser().parse_args()

    update_env_deployment_info(args.dirname, args.action)


if __name__ == "__main__":
    main()
