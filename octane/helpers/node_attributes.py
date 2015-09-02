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


def copy_ifaces(src, dst):
    def pull(ifaces):
        for iface in ifaces:
            yield (iface['name'],
                   iface['assigned_networks'])

    def push(ifaces, assignments, nets):
        for iface in ifaces:
            networks = assignments.get(iface['name'], [])
            networks = [{'id': nets[net['name']],
                         'name': net['name']} for net in networks]
            yield dict(iface,
                       assigned_networks=networks,
                       )

    nets = {}
    for iface in dst:
        nets.update(dict([(net['name'], net['id'])
                          for net in iface['assigned_networks']]))
    assignments = pull(src)
    ifaces = push(dst, dict(assignments), nets)
    return ifaces


def by_extra(disk):
    return ''.join(sorted(disk['extra']))


def by_name(disk):
    return disk['name']


KEY_FUNCS = {
    'by_extra': by_extra,
    'by_name': by_name,
}


def copy_disks(src, dst, method):
    key_func = KEY_FUNCS[method]

    def pull(disks):
        for disk in disks:
            yield (key_func(disk),
                   disk['volumes'])

    def push(disks1, disks2):
        def to_dict(attrs):
            return dict((key_func(attr), attr) for attr in attrs)

        dict_disks1 = to_dict(disks1)
        for extra, volumes in disks2:
            dict_disks1[extra].update(volumes=volumes)
            yield dict_disks1[extra]

    fixture_disks = pull(src)
    disks = push(dst, fixture_disks)

    return disks
