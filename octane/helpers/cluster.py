import requests
import urlparse
import os
import json

from keystoneclient.v2_0 import Client as keystoneclient


class NailgunClient(object):

    def __init__(self, admin_node_ip, **kwargs):
        self.url = "http://{0}:8000".format(admin_node_ip)
        keystone_url = "http://{0}:5000/v2.0".format(admin_node_ip)
        ksclient = keystoneclient(auth_url=keystone_url, **kwargs)
        self.headers = {"X-Auth-Token": ksclient.auth_token,
                        "Content-Type": "application/json"}

    def _get_cluster_list(self):
        endpoint = urlparse.urljoin(self.url, "api/clusters")
        return requests.get(endpoint, headers=self.headers).json()

    def _get_cluster(self, cluster_id):
        endpoint = urlparse.urljoin(self.url,
                                    "api/clusters/{0}".format(cluster_id))
        return requests.get(endpoint, headers=self.headers).json()

    def _get_cluster_attributes(self, cluster_id):
        endpoint = urlparse.urljoin(self.url,
                                    "api/clusters/{0}/attributes".format(
                                        cluster_id))
        return requests.get(endpoint, headers=self.headers).json()

    def _get_list_nodes(self):
        endpoint = urlparse.urljoin(self.url, "api/nodes")
        return requests.get(endpoint, headers=self.headers).json()

    def _get_list_networks(self, cluster_id):
        net_provider = self._get_cluster(cluster_id)["net_provider"]
        endpoint = urlparse.urljoin(self.url,
                                    "/api/clusters/{0}"
                                    "/network_configuration/{1}".format(
                                        cluster_id, net_provider))
        return requests.get(endpoint, headers=self.headers).json()

    def _create_cluster(self, data):
        endpoint = urlparse.urljoin(self.url, "api/clusters")
        return requests.post(endpoint, headers=self.headers,
                             data=json.dumps(data))

    def list_cluster_nodes(self, cluster_id):
        endpoint = urlparse.urljoin(
            self.url, "api/nodes/?cluster_id={0}".format(cluster_id))
        return requests.get(endpoint, headers=self.headers).json()

    def update_cluster_attributes(self, cluster_id, attrs):
        endpoint = urlparse.urljoin(
            self.url, "api/clusters/{0}/attributes".format(cluster_id))
        return requests.put(endpoint, headers=self.headers,
                            data=json.dumps(attrs))

    def update_node(self, node_id, data):
        endpoint = urlparse.urljoin(self.url, "api/nodes/{0}".format(node_id))
        return requests.put(endpoint, headers=self.headers,
                            data=json.dumps(data))

    def get_node_interfaces(self, node_id):
        endpoint = urlparse.urljoin(self.url,
                                    "api/nodes/{0}/interfaces".format(node_id))
        return requests.get(endpoint, headers=self.headers).json()

    def put_node_interfaces(self, data):
        """

        :param data: [{'id': node_id, 'interfaces': interfaces}]
        :return: response
        """
        endpoint = urlparse.urljoin(self.url, "api/nodes/interfaces")
        return requests.put(endpoint, headers=self.headers,
                            data=json.dumps(data))

    def update_cluster_networks(self, cluster_id, data):
        net_provider = self._get_cluster(cluster_id)["net_provider"]
        endpoint = urlparse.urljoin(
            self.url,
            "api/clusters/{0}/network_configuration/{1}".format(cluster_id,
                                                                net_provider))
        return requests.put(endpoint, headers=self.headers,
                            data=json.dumps(data))

    def get_node_disks(self, node_id):
        endpoint = urlparse.urljoin(self.url,
                                    "api/nodes/{0}/disks".format(node_id))
        return requests.get(endpoint, headers=self.headers).json()

    def put_node_disks(self, node_id, data):
        endpoint = urlparse.urljoin(self.url,
                                    "api/nodes/{0}/disks".format(node_id))
        return requests.put(endpoint, headers=self.headers,
                            data=json.dumps(data))

    def get_releases(self):
        endpoint = urlparse.urljoin(self.url, "api/releases")
        return requests.get(endpoint, headers=self.headers)

    def get_release_details(self, release_id):
        endpoint = urlparse.urljoin(self.url, "api/releases/{0}".format(
            release_id))
        return requests.get(endpoint, headers=self.headers)


def dump_cluster(cluster_name, fuel_node, user="admin", password="admin",
                 tenant="admin"):
    client = NailgunClient(fuel_node, username=user, password=password,
                           tenant_name=tenant)

    def get_cluster_id(cluster_name):
        for cluster in client._get_cluster_list():
            if cluster["name"] == cluster_name:
                return cluster["id"]
        else:
            raise NameError("Can not find cluster with specified name")

    cluster_id = get_cluster_id(cluster_name)
    os.makedirs(cluster_name)

    with open("{0}/cluster.json".format(cluster_name), "w") as cluster:
        json.dump(client._get_cluster(cluster_id), cluster, sort_keys=False,
                  indent=4)

    with open("{0}/cluster_attributes.json".format(cluster_name),
              "w") as cluster_attrs:
        json.dump(client._get_cluster_attributes(cluster_id), cluster_attrs,
                  sort_keys=False, indent=4)

    with open("{0}/cluster_networks.json".format(
            cluster_name), "w") as cluster_net:
        json.dump(client._get_list_networks(cluster_id), cluster_net,
                  sort_keys=False, indent=4)

    for node in client.list_cluster_nodes(cluster_id):
        with open("{0}/node-{1}.json".format(cluster_name, node["id"]),
                  "w") as node_cfg:
            json.dump(node, node_cfg, sort_keys=False, indent=4)

        with open(
                "{0}/node-{1}-networks.json".format(cluster_name,
                                                    node["id"]),
                "w") as node_net:
            json.dump(client.get_node_interfaces(node["id"]), node_net,
                      sort_keys=False, indent=4)

        with open(
                "{0}/node-{1}-disks.json".format(cluster_name,
                                                 node["id"]),
                "w") as node_disks:
            json.dump(client.get_node_disks(node["id"]), node_disks,
                      sort_keys=False, indent=4)


def restore_cluster(folder, fuel_node, user="admin", password="admin",
                    tenant="admin", upgrade=None):
    client = NailgunClient(fuel_node, username=user, password=password,
                           tenant_name=tenant)

    if os.path.isfile("{0}/cluster.json".format(folder)):
        with open("{0}/cluster.json".format(folder)) as cluster:
            cluster_data = json.load(cluster)

        needed_version = cluster_data["release_id"]

        if upgrade:
            restore_cluster_os_version = client.get_release_details(
                cluster_data["release_id"]).json()["name"].split()[:3]
            for release in [i for i in client.get_releases().json()
                            if int(i["id"]) > int(cluster_data["release_id"])]:
                os_ver = release["name"].split()
                if restore_cluster_os_version[0] != os_ver[0] and \
                        restore_cluster_os_version[2] == os_ver[2]:
                    needed_version = release["id"]

        new_cluster_data = {
            "name": cluster_data["name"],
            "release": needed_version,
            "mode": cluster_data["mode"],
            "net_provider": cluster_data["net_provider"]
        }
        if cluster_data.get("net_segment_type"):
            new_cluster_data["net_segment_type"] = cluster_data[
                "net_segment_data"]
        elif os.path.isfile("{0}/cluster_networks.json".format(folder)):
            with open(
                    "{0}/cluster_networks.json".format(folder)
            ) as cluster_nets:
                cluster_nets_data = json.load(cluster_nets)
                if cluster_data["net_provider"] == "neutron":
                    new_cluster_data["net_segment_type"] = \
                        cluster_nets_data["networking_parameters"][
                            "segmentation_type"]
                else:
                    new_cluster_data["net_manager"] = \
                        cluster_nets_data["networking_parameters"][
                            "net_manager"]

        new_clust = client._create_cluster(new_cluster_data).json()
    else:
        raise NameError("Can not find cluster.json")

    if os.path.isfile("{0}/cluster_attributes.json".format(folder)):
        with open(
                "{0}/cluster_attributes.json".format(folder)) as cluster_attrs:
            cluster_attrs_data = json.load(cluster_attrs)
        restore_cluster_attrs = client._get_cluster_attributes(new_clust["id"])
        for k, _ in cluster_attrs_data["editable"].items():
            for k1, v1 in cluster_attrs_data["editable"][k].items():
                if "value" in v1:
                    if "value" in restore_cluster_attrs["editable"].get(
                            k, {}).get(k1, {}):
                        restore_cluster_attrs["editable"][k][k1]["value"] = v1[
                            "value"]
                elif "values" in v1:
                    if "values" in restore_cluster_attrs["editable"].get(
                            k, {}).get(k1, {}):
                        restore_cluster_attrs[
                            "editable"][k][k1]["values"] = v1["values"]

        client.update_cluster_attributes(new_clust["id"],
                                         restore_cluster_attrs)

    if os.path.isfile("{0}/cluster_networks.json".format(folder)):
        with open("{0}/cluster_networks.json".format(folder)) as cluster_nets:
            cluster_nets_data = json.load(cluster_nets)

        restore_cluster_nets_data = client._get_list_networks(new_clust["id"])
        for key, value in cluster_nets_data["networking_parameters"].items():
            if key == "base_mac":
                continue
            restore_cluster_nets_data["networking_parameters"][key] = value

        for net in cluster_nets_data["networks"]:
            if net["name"] == "fuelweb_admin":
                continue
            for new_net in restore_cluster_nets_data["networks"]:
                if net["name"] == new_net["name"]:
                    for key, value in net.items():
                        if key in ["cluster_id", "id", "meta", "group_id"]:
                            continue
                        new_net[key] = value

        client.update_cluster_networks(new_clust["id"],
                                       restore_cluster_nets_data)
