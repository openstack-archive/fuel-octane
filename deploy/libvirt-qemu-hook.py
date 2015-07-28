#!/usr/bin/python3
# Taken from https://github.com/nileshgr/utilities/blob/master/admin/libvirt-qemu-hook.py

'''
This script was written for Python 3.
I do not know if it will work on Python 2.
'''

'''
LibVirt hook for setting up port forwards when using 
NATed networking.

Setup port spec below in the mapping dict.

Copy file to /etc/libvirt/hooks/<your favorite name>

chmod +x /etc/libvirt/hooks/<your favorite name>

restart libvirt

And it should work
'''

import os
import re
import subprocess
import sys

iptables='/sbin/iptables'

def get_ip(interface):
    res = subprocess.check_output(['ip', 'addr', 'show', 'dev', interface])
    m = re.search(b'inet ([0-9.]+)', res)
    if not m:
        raise RuntimeException("Address not found")
    return m.group(1).decode()

mapping = {
    'fuel': { 
        'ip': '10.20.0.2', 
        'publicip': get_ip('p1p1'),
        'portmap': {
            'tcp': [(2222, 22), (8000, 8000)],
        }
    },
}

def rules(act, map_dict):
    if map_dict['portmap'] == 'all':
        cmd = '{} -t nat {} PREROUTING -d {} -j DNAT --to {}'.format(iptables, act, map_dict['publicip'], map_dict['ip'])
        os.system(cmd)
        cmd = '{} -t nat {} POSTROUTING -s {} -j SNAT --to {}'.format(iptables, act, map_dict['ip'], map_dict['publicip'])
        os.system(cmd)
        cmd = '{} -t filter {} FORWARD -d {} -j ACCEPT'.format(iptables, act, map_dict['ip'])
        os.system(cmd)
        cmd = '{} -t filter {} FORWARD -s {} -j ACCEPT'.format(iptables, act, map_dict['ip'])
        os.system(cmd)
    else:
        cmd = '{} -t filter {} FORWARD -d {} -p icmp -j ACCEPT'.format(iptables, act, map_dict['ip'])
        os.system(cmd)
        cmd = '{} -t filter {} FORWARD -s {} -p icmp -j ACCEPT'.format(iptables, act, map_dict['ip'])
        os.system(cmd)
        for proto in map_dict['portmap']:
            for portmap in map_dict['portmap'].get(proto):
                cmd = '{} -t nat {} PREROUTING -d {} -p {} --dport {} -j DNAT --to {}:{}'.format(iptables, act, map_dict['publicip'], proto, str(portmap[0]), map_dict['ip'], str(portmap[1]))
                os.system(cmd)
                cmd = '{} -t filter {} FORWARD -d {} -p {} --dport {} -j ACCEPT'.format(iptables, act, map_dict['ip'], proto, str(portmap[1]))
                os.system(cmd)
                cmd = '{} -t filter {} FORWARD -s {} -p {} --sport {} -j ACCEPT'.format(iptables, act, map_dict['ip'], proto, str(portmap[1]))
                os.system(cmd)

if __name__ == '__main__':
    domain=sys.argv[1]
    action=sys.argv[2]

    host=mapping.get(domain)

    if host is None:
        sys.exit(0)

    if action == 'stopped' or action == 'reconnect':
        rules('-D', host)

    if action == 'start' or action == 'reconnect':
        rules('-I', host)
