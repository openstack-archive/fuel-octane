import argparse
import yaml


parser = argparse.ArgumentParser(description="ips copy script")
parser.add_argument('source_yaml', metavar='<file>', type=str,
                    help='source yaml file')
parser.add_argument('destination_yaml', metavar='<file>', type=str,
                    help='destination yaml file')
args = parser.parse_args()

with open(args.source_yaml, 'r') as source:
    source_yaml = yaml.load(source)

with open(args.destination_yaml, 'r') as dest:
    dest_yaml = yaml.load(dest)
    dest_yaml["management_vip"] = source_yaml["management_vip"]
    dest_yaml["public_vip"] = source_yaml["public_vip"]
    for i in source_yaml["nodes"]:
        for j in dest_yaml["nodes"]:
            if i["name"] == j["name"] and i["role"] in ["controller",
                                                        "primary-controller"]:
                j["internal_address"] = i["internal_address"]
                j["public_address"] = i["public_address"]

with open(args.destination_yaml, 'w') as target:
    target.write(yaml.dump(dest_yaml, default_flow_style=False))
