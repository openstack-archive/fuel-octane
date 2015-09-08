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
            yield (name, [{
                'id': mapping[n['name']],
                'name': n['name'],
            } for n in networks])

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
