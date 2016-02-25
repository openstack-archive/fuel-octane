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

import argparse

import glanceclient.client
import keystoneclient.v2_0.client as ksclient
import neutronclient.neutron.client


parser = argparse.ArgumentParser(description="Remove fuel resources from node")
parser.add_argument('--skip-neutron', action='store_true',
                    help='source yaml file')
args = parser.parse_args()


def _get_keystone(username, password, tenant_name, auth_url):
    return ksclient.Client(username=username,
                           password=password,
                           tenant_name=tenant_name,
                           auth_url=auth_url)


def _get_glance(version=2, endpoint=None, token=None):
    return glanceclient.client.Client(version, endpoint=endpoint,
                                      token=token)


def _get_neutron(version='2.0', token=None, endpoint_url=None):
    return neutronclient.neutron.client.Client(version,
                                               token=token,
                                               endpoint_url=endpoint_url)


def clean_neutron_resources(neutron):
    for i in neutron.list_floatingips()["floatingips"]:
        neutron.delete_floatingip(i["id"])
    for router in neutron.list_routers()["routers"]:
        neutron.remove_gateway_router(router['id'])
        for j in neutron.list_subnets()["subnets"]:
            try:
                neutron.remove_interface_router(router['id'],
                                                {"subnet_id": j["id"]})
            except Exception:
                pass
            neutron.delete_subnet(j["id"])
        neutron.delete_router(router['id'])
    for network in neutron.list_networks()["networks"]:
        neutron.delete_network(network["id"])


def clenup_resources(username, password, tenant_name, auth_url):
    keystone = _get_keystone(username, password, tenant_name, auth_url)

    glance_endpoint = keystone.service_catalog.url_for(
        service_type='image',
        endpoint_type='publicURL')
    glance = _get_glance(endpoint=glance_endpoint, token=keystone.auth_token)
    neutron_endpoint = keystone.service_catalog.url_for(
        service_type='network',
        endpoint_type='publicURL')

    for image in glance.images.list():
        glance.images.delete(image["id"])

    if not args.skip_neutron:
        neutron = _get_neutron(token=keystone.auth_token,
                               endpoint_url=neutron_endpoint)
        clean_neutron_resources(neutron)


if __name__ == '__main__':
    import os
    clenup_resources(
        os.environ["OS_USERNAME"],
        os.environ["OS_PASSWORD"],
        os.environ["OS_TENANT_NAME"],
        os.environ["OS_AUTH_URL"],
    )
