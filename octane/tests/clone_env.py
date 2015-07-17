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

import json
import requests
import urlparse

import testresources
import testtools

from keystoneclient.v2_0 import Client as keystoneclient


class CloneEnvTests(testtools.TestCase, testtools.testcase.WithAttributes,
                    testresources.ResourcedTestCase):

    @classmethod
    def setUpClass(cls):
        super(CloneEnvTests, cls).setUpClass()
        cls.url = "http://10.20.0.2:8000"
        keystone_url = "http://10.20.0.2:5000/v2.0"
        cls.endpoint = urlparse.urljoin(cls.url,
                                        "api/clusters/1/upgrade/clone")
        ksclient = keystoneclient(auth_url=keystone_url, username="admin",
                                  password="admin", tenant_name="admin")
        cls.headers = {"X-Auth-Token": ksclient.auth_token,
                       "Content-Type": "application/json"}
        cls.clusters = []

    def tearDown(self):
        super(CloneEnvTests, self).tearDown()
        for cluster in self.clusters:
            self._delete_cluster(cluster)

    def _delete_cluster(self, cluster_id):
        endpoint = urlparse.urljoin(self.url,
                                    "api/clusters/{0}".format(cluster_id))
        return requests.delete(endpoint, headers=self.headers)

    def _get_cluster(self, cluster_id):
        endpoint = urlparse.urljoin(self.url,
                                    "api/clusters/{0}".format(cluster_id))
        return requests.get(endpoint, headers=self.headers).json()

    def _get_cluster_attributes(self, cluster_id):
        endpoint = urlparse.urljoin(self.url,
                                    "api/clusters/{0}/attributes".format(
                                        cluster_id))
        return requests.get(endpoint, headers=self.headers).json()

    def _get_releases(self):
        endpoint = urlparse.urljoin(self.url, "api/releases")
        return requests.get(endpoint, headers=self.headers).json()

    def _get_release_details(self, release_id):
        endpoint = urlparse.urljoin(self.url, "api/releases/{0}".format(
            release_id))
        return requests.get(endpoint, headers=self.headers).json()

    def _get_list_networks(self, cluster_id):
        net_provider = self._get_cluster(cluster_id)["net_provider"]
        endpoint = urlparse.urljoin(self.url,
                                    "/api/clusters/{0}"
                                    "/network_configuration/{1}".format(
                                        cluster_id, net_provider))
        return requests.get(endpoint, headers=self.headers).json()

    def _get_deployable_release_id(self, cluster_id):
        cluster = self._get_cluster(cluster_id)
        releases = self._get_releases()
        release_details = self._get_release_details(cluster["release_id"])

        if release_details["is_deployable"]:
            return release_details["id"]
        else:
            return next(release["id"]
                        for release in releases
                        if release["id"] > cluster["release_id"] and
                        release["operating_system"] == release_details[
                        "operating_system"] and release["is_deployable"])

    def test_env_clone_to_deployable_release_id(self):
        cluster = self._get_cluster(1)
        release_id = self._get_deployable_release_id(1)

        post_body = {
            "name": "new_test_cluster",
            "release_id": release_id
        }

        resp = requests.post(self.endpoint, data=json.dumps(post_body),
                             headers=self.headers)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(release_id, resp.json()["release_id"])
        self.assertEqual(cluster["net_provider"], resp.json()["net_provider"])
        self.assertEqual(cluster["mode"], resp.json()["mode"])

        self.clusters.append(resp.json()["id"])

        cluster = self._get_cluster_attributes(1)
        cloned_cluster = self._get_cluster_attributes(resp.json()["id"])

        for key in cloned_cluster["editable"]:
            if key == "repo_setup":
                continue
            for key1, value1 in cloned_cluster["editable"][key].items():
                if "value" in value1:
                    if "value" in cluster["editable"].get(key, {}).get(
                            key1, {}):
                        self.assertEqual(
                            cluster["editable"][key][key1]["value"],
                            value1["value"])

                elif "values" in value1:
                    if "values" in cluster["editable"].get(key, {}).get(
                            key1, {}):
                        self.assertEqual(
                            cluster["editable"][key][key1]["values"],
                            value1["values"])

        old_cluster_net_cfg = self._get_list_networks(1)
        new_cluster_net_cfg = self._get_list_networks(resp.json()["id"])

        self.assertEqual(old_cluster_net_cfg["management_vip"],
                         new_cluster_net_cfg["management_vip"])
        self.assertEqual(old_cluster_net_cfg["public_vip"],
                         new_cluster_net_cfg["public_vip"])

        for parameter in new_cluster_net_cfg["networking_parameters"]:
            if parameter in old_cluster_net_cfg["networking_parameters"]:
                self.assertEqual(
                    old_cluster_net_cfg["networking_parameters"][parameter],
                    new_cluster_net_cfg["networking_parameters"][parameter])

        for network in new_cluster_net_cfg["networks"]:
            if network["name"] not in ["public", "management", "storage"]:
                continue
            for old_network in old_cluster_net_cfg["networks"]:
                if network["name"] == old_network["name"] and network["name"]:
                    self.assertEqual(old_network["cidr"], network["cidr"])
                    self.assertEqual(old_network["ip_ranges"],
                                     network["ip_ranges"])
                    self.assertEqual(old_network["vlan_start"],
                                     network["vlan_start"])

    def test_clone_nonexistent_cluster(self):
        endpoint = urlparse.urljoin(self.url,
                                    "api/clusters/xa/upgrade/clone")
        post_body = {
            "name": "new_test_cluster",
            "release_id": 123456
        }

        resp = requests.post(endpoint, data=json.dumps(post_body),
                             headers=self.headers)

        self.assertEqual(404, resp.status_code)

    def test_clone_wo_name_in_body(self):
        self.skip("https://mirantis.jira.com/browse/OCTANE-124")
        release_id = self._get_deployable_release_id(1)

        post_body = {
            "release_id": release_id
        }

        resp = requests.post(self.endpoint, data=json.dumps(post_body),
                             headers=self.headers)

        self.assertEqual(400, resp.status_code)

    def test_clone_wo_release_id_in_body(self):
        self.skip("https://mirantis.jira.com/browse/OCTANE-124")
        post_body = {
            "name": "new_test_cluster"
        }

        resp = requests.post(self.endpoint, data=json.dumps(post_body),
                             headers=self.headers)

        self.assertEqual(400, resp.status_code)

    def test_clone_with_empty_body(self):

        resp = requests.post(self.endpoint, data=None,
                             headers=self.headers)

        self.assertEqual(400, resp.status_code)

    def test_clone_with_too_long_name(self):
        self.skip("https://mirantis.jira.com/browse/OCTANE-124")
        release_id = self._get_deployable_release_id(1)

        post_body = {
            "name":
                "MANYMANYSYMBOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOLSSS",
            "release_id": release_id
        }

        resp = requests.post(self.endpoint, data=json.dumps(post_body),
                             headers=self.headers)

        self.assertEqual(400, resp.status_code)

    def test_clone_with_nonexistent_release_id(self):
        post_body = {
            "name": "new_test_cluster",
            "release_id": 123456
        }

        resp = requests.post(self.endpoint, data=json.dumps(post_body),
                             headers=self.headers)

        self.assertEqual(404, resp.status_code)

    def test_clone_with_incorrect_release_id(self):
        post_body = {
            "name": "new_test_cluster",
            "release_id": "djigurda"
        }

        resp = requests.post(self.endpoint, data=json.dumps(post_body),
                             headers=self.headers)

        self.assertEqual(400, resp.status_code)
