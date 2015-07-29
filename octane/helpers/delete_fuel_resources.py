import glanceclient.client
import neutronclient.neutron.client
import keystoneclient.v2_0.client as ksclient


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


def clenup_resources(username, password, tenant_name, auth_url):
    keystone = _get_keystone(username, password, tenant_name, auth_url)

    glance_endpoint = keystone.service_catalog.url_for(
        service_type='image',
        endpoint_type='publicURL')
    glance = _get_glance(endpoint=glance_endpoint, token=keystone.auth_token)
    neutron_endpoint = keystone.service_catalog.url_for(
        service_type='network',
        endpoint_type='publicURL')
    neutron = _get_neutron(token=keystone.auth_token,
                           endpoint_url=neutron_endpoint)

    for image in glance.images.list():
        glance.images.delete(image["id"])

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

if __name__ == '__main__':
    import os
    clenup_resources(
        os.environ["OS_USERNAME"],
        os.environ["OS_PASSWORD"],
        os.environ["OS_TENANT_NAME"],
        os.environ["OS_AUTH_URL"],
    )
