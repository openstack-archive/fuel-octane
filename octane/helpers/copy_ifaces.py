import sys

import yaml


def main():
    def pull(ifaces):
        for iface in ifaces:
            yield (iface['name'],
                   iface['assigned_networks'])

    def push(ifaces, assignments):
        for iface in ifaces:
            networks = assignments.get(iface['name'], [])
            yield dict(iface,
                       assigned_networks=networks,
                       )

    src = yaml.load(open(sys.argv[1]))
    dst = yaml.load(open(sys.argv[2]))

    assignments = pull(src)
    ifaces = push(dst, dict(assignments))

    yaml.dump(list(ifaces), stream=sys.stdout, default_flow_style=False)


if __name__ == '__main__':
    main()

