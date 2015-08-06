import neutronclient.neutron.client
import keystoneclient.v2_0.client as ksclient
from novaclient import client as nova


def _get_keystone(username, password, tenant_name, auth_url):
    return ksclient.Client(username=username,
                           password=password,
                           tenant_name=tenant_name,
                           auth_url=auth_url)


def _get_neutron(version='2.0', token=None, endpoint_url=None):
    return neutronclient.neutron.client.Client(version,
                                               token=token,
                                               endpoint_url=endpoint_url)


class TestResourcesGenerator(object):
    def __init__(self, username, password, tenant_name, keystone_url):
        self.keystone = _get_keystone(username, password, tenant_name,
                                      keystone_url)

        self.nova = nova.Client("2", auth_token=self.keystone.auth_token)
        compute_api_url = self.keystone.service_catalog.url_for(
            service_type="compute",
            endpoint_type='publicURL')
        self.nova.set_management_url(compute_api_url)
        neutron_endpoint = self.keystone.service_catalog.url_for(
            service_type='network',
            endpoint_type='publicURL')
        self.neutron = _get_neutron(token=self.keystone.auth_token,
                                    endpoint_url=neutron_endpoint)

        self.tenant_id = self.keystone.tenant_id

    def _create_router(self, name):
        external_network = None
        for network in self.neutron.list_networks()["networks"]:
            if network.get("router:external"):
                external_network = network
                break

        if not external_network:
            raise Exception("Alarm! Can not to find external network")

        gw_info = {
            "network_id": external_network["id"],
            "enable_snat": True
        }

        router_info = {
            "router": {
                "name": name,
                "external_gateway_info": gw_info,
                "tenant_id": self.tenant_id
            }
        }

        router = self.neutron.create_router(router_info)['router']

        return router

    def _create_network(self, name):
        internal_network_info = {
            "network": {
                "name": name,
                "tenant_id": self.tenant_id
            }
        }

        network = self.neutron.create_network(
            internal_network_info)['network']

        return network

    def _create_subnet(self, internal_network, cidr):
        subnet_info = {
            "subnet": {
                "network_id": internal_network['id'],
                "ip_version": 4,
                "cidr": cidr,
                "tenant_id": self.tenant_id
            }
        }

        subnet = self.neutron.create_subnet(subnet_info)['subnet']

        return subnet

    def _uplink_subnet_to_router(self, router, subnet):
        return self.neutron.add_interface_router(
            router["id"], {"subnet_id": subnet["id"]})

    def _create_server(self, server_name, image_id, flavor_id,
                       security_group, nic):
        return self.nova.servers.create(server_name, image_id, flavor_id,
                                        security_groups=[security_group],
                                        nics=[{'net-id': nic}],
                                        userdata=open("meta.txt"))

    def infra_generator(self, networks_count, vms_per_net):
        flavor = self.nova.flavors.create(name="testflav", ram=128, disk=5,
                                          vcpus=1)
        image_id = self.nova.images.list()[0].id

        for network in self.neutron.list_networks()["networks"]:
            if network.get("router:external"):
                external_network = network
        needed_ips = networks_count*vms_per_net - len(
            self.neutron.list_floatingips())
        if needed_ips > 0:
            for i in xrange(needed_ips):
                self.neutron.create_floatingip(
                    {
                        'floatingip': {
                            'floating_network_id': external_network["id"]
                        }
                    }
                )
        floatingip_list = self.neutron.list_floatingips()['floatingips']

        for net in xrange(networks_count):
            router = self._create_router("testrouter{0}".format(net))
            network = self._create_network("testnet{0}".format(net))
            subnet = self._create_subnet(network, "12.0.{0}.0/24".format(net))
            self._uplink_subnet_to_router(router, subnet)
            for vm in xrange(vms_per_net):
                server = self._create_server("testserver{0}{1}".format(net,
                                                                       vm),
                                             image_id,
                                             flavor.id,
                                             "default",
                                             network["id"])
                port_id = server.interface_list()[0].port_id
                self.neutron.update_floatingip(floatingip_list.pop()['id'],
                                               {'floatingip': {
                                                   'port_id': port_id}})


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Cleanup script")
    parser.add_argument('username', metavar='<user>', type=str,
                        help='admin username')
    parser.add_argument('password', metavar='<password>', type=str,
                        help='admin password')
    parser.add_argument('tenant_name', metavar='<tenant_name>', type=str,
                        help='admin tenant')
    parser.add_argument('keystone_url', metavar='<keystone_url>', type=str,
                        help='Keystone url')
    args = parser.parse_args()

    generator = TestResourcesGenerator(args.username, args.password,
                                       args.tenant_name,
                                       args.keystone_url)
    generator.infra_generator(3, 5)
