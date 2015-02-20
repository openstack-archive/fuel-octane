import yaml
import os
import re
import argparse


def get_parser():
    parser = argparse.ArgumentParser(description="Remove patch ports from "
                                                 "deployment configuration "
                                                 "of environment")
    parser.add_argument("dirname",
                        help="Name of directory that contains deployment "
                             "configuration of environment")
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
    return host_config, action


def update_host_deployment_info(host_file, bridges):
    host_config = load_yaml_file(host_file)
    removed_actions = []
    for bridge_name in bridges:
        host_config, removed_action = remove_patch_port(host_config,
                                                        bridge_name)
        removed_actions.append(removed_action)
    dump_yaml_file(host_config, host_file)
    return removed_actions


def update_env_deployment_info(dirname):
    pattern = "^[-\w]+_\d+.yaml$"
    bridges = ['br-ex', 'br-mgmt']
    host_files = os.listdir(dirname)
    for filename in host_files:
        if re.match(pattern, filename):
            host_file = os.path.join(dirname, filename)
            update_host_deployment_info(host_file, bridges)


def patch_port_params(host_file, bridge_name):
    host_config = load_yaml_file(host_file)
    transformations = host_config['network_scheme']['transformations']
    patches = [action for action in transformations
               if (action['action'] == 'add-patch')
               and (bridge_name in action['bridges'])]
    return([(patch['bridges'], patch['trunks']) for patch in patches])


def main():
    args = get_parser().parse_args()

    update_env_deployment_info(args.dirname)


if __name__ == "__main__":
    main()
