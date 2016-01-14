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

import logging
import os
import yaml

from octane.handlers.backup_restore import base

LOG = logging.getLogger(__name__)


class AstuteArchivator(base.PathArchivator):
    PATH = "/etc/fuel/astute.yaml"
    NAME = "astute/astute.yaml"

    KEYS_TO_RESTORE = [
        ("HOSTNAME", None),
        ("DNS_DOMAIN", None),
        ("DNS_SEARCH", None),
        ("DNS_UPSTREAM", None),
        ("ADMIN_NETWORK", [
            "interface",
            "ipaddress",
            "netmask",
            "mac",
            "dhcp_pool_start",
            "dhcp_pool_end",
            "dhcp_gateway",
        ]),
        ("astute", ["user", "password"]),
        ("cobbler", ["user", "password"]),
        ("keystone", [
            "admin_token",
            "ostf_user",
            "ostf_password",
            "nailgun_user",
            "nailgun_password",
            "monitord_user",
            "monitord_password",
        ]),
        ("mcollective", ["user", "password"]),
        ("postgres", [
            "keystone_dbname",
            "keystone_user",
            "keystone_password",
            "nailgun_dbname",
            "nailgun_user",
            "nailgun_password",
            "ostf_dbname",
            "ostf_user",
            "ostf_password",
        ]),
        ("FUEL_ACCESS", ["user", "password"]),
    ]

    def restore(self):
        dump = self.archive.extractfile(self.NAME)
        if not os.path.exists(self.PATH):
            raise Exception("no astute etc file")
        backup_yaml = yaml.load(dump)
        with open(self.PATH, "r") as current:
            current_yaml = yaml.load(current)
        not_found_keys = []
        for key, subkeys in self.KEYS_TO_RESTORE:
            if not subkeys and key not in backup_yaml:
                not_found_keys.extend(key)
                continue
            if not subkeys:
                current_yaml[key] = backup_yaml[key]
                continue
            backup_values = backup_yaml.get(key, {})
            current_yaml[key] = current_yaml.get(key, {})
            for subkey in subkeys:
                if subkey not in backup_values:
                    not_found_keys.append("{0}/{1}".format(key, subkey))
                else:
                    current_yaml[key][subkey] = backup_values[subkey]
        if not_found_keys:
            LOG.error(
                "Not found values in backup for keys: {0}".format(
                    ",".join(not_found_keys)))
        with open(self.PATH, "w") as new:
            yaml.safe_dump(current_yaml, new, default_flow_style=False)
