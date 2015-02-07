import yaml
import os
import re

def load_yaml_file(filename):
    with open(filename) as f:
        return yaml.safe_load(f)


def dump_yaml_file(dict_obj, filename):
    with open(filename, 'w') as f:
        yaml.dump(dict_obj, f, default_flow_style=False)


def remove_patch_port(host_config, bridge_name):
    transformations = host_config['network_scheme']['transformations']
    for action in transformations:
        if (action['action'] == 'add-patch') and 
                (bridge_name in action['bridges']):
            transformation.remove[action]
    return host_config


def update_host_deployment_info(host_file, bridges):
    host_config = load_yaml_file(host_file)
    for bridge_name in bridges:
        host_config = remove_patch_port(host_config, bridge_name)
    dump_yaml_file(host_config, host_file)


def update_env_deployment_info(env_id):
    dirname = "deployment_{0}".format(env_id)
    pattern = "^\w*-?controller_\d+.yaml$"
    bridges = ['br-ex', 'br-mgmt']
    host_files = os.listdir(dirname)
    for filename in host_files:
        if re.match(pattern, host_file):
            host_file = os.path.join(dirname, filename)
            update_host_deployment_info(host_file, bridges)
