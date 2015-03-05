import sys

import yaml


def main():
    def pull(ifaces):
        for iface in ifaces:
            yield (iface['name'],
                   iface['assigned_networks'])

    def merge(src, dst):
        mapping = dict((a['name'], a['id']) for _, ns in dst for a in ns)
        for name, networks in src:
            yield (name,
                   [{
                        'id': mapping[n['name']],
                        'name': n['name'],
                    }
                    for n in networks])

    def push(ifaces, assignments):
        for iface in ifaces:
            networks = assignments.get(iface['name'], [])
            yield dict(iface,
                       assigned_networks=networks,
                       )

    src = yaml.load(open(sys.argv[1]))
    dst = yaml.load(open(sys.argv[2]))

    src_assign = pull(src)
    dst_assign = pull(dst)
    assign = merge(src_assign, dst_assign)
    ifaces = push(dst, dict(assign))

    yaml.dump(list(ifaces), stream=sys.stdout, default_flow_style=False)


if __name__ == '__main__':
    main()

