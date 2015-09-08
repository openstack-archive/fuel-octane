#!/usr/bin/python
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
import os
import sys

from neutronclient.v2_0 import client as neutron_client
from novaclient.v2 import client as nova_client


def cleanup_nova_services(access_data, hosts):
    client = nova_client.Client(
        access_data['user'],
        access_data['password'],
        access_data['tenant'],
        access_data['auth_url']
    )
    services = client.services.list()
    for service in services:
        if service.host not in hosts:
            client.services.delete(service.id)


def cleanup_neutron_agents(access_data, hosts):
    client = neutron_client.Client(
        username=access_data['user'],
        password=access_data['password'],
        tenant_name=access_data['tenant'],
        auth_url=access_data['auth_url']
    )
    agents = client.list_agents()
    for agent in agents['agents']:
        if agent['host'] not in hosts:
            client.delete_agent(agent['id'])


def main():
    hosts = sys.stdin.readlines()
    access_data = {
        'user': os.environ['OS_USERNAME'],
        'password': os.environ['OS_PASSWORD'],
        'tenant': os.environ['OS_TENANT_NAME'],
        'auth_url': os.environ['OS_AUTH_URL'],
    }

    cleanup_nova_services(access_data, hosts)
    cleanup_neutron_agents(access_data, hosts)


if __name__ == '__main__':
    main()
