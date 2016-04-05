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
import shutil
import yaml

from octane.handlers.backup_restore import base
from octane.util import puppet


LOG = logging.getLogger(__name__)


class AstuteArchivator(base.PathArchivator):
    path = "/etc/fuel/astute.yaml"
    name = "astute/astute.yaml"

    keys_to_restore = [
        ("HOSTNAME", None),
        ("DNS_DOMAIN", None),
        ("DNS_SEARCH", None),
        ("DNS_UPSTREAM", None),
        ("ADMIN_NETWORK", [
            "ipaddress",
            "netmask",
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

    def get_backup_dict(self):
        return yaml.load(self.archive.extractfile(self.name))

    def get_current_dict(self):
        with open(self.path, "r") as current:
            return yaml.load(current)

    def pre_restore_check(self):
        backup_ip = self.get_backup_dict()["ADMIN_NETWORK"]["ipaddress"]
        current_ip = self.get_current_dict()["ADMIN_NETWORK"]["ipaddress"]
        if backup_ip != current_ip:
            raise Exception(
                "Restore allowed on machine with same ipaddress. "
                "Use fuel-menu to set up ipaddress to {0}".format(backup_ip))

    def restore(self):
        backup_yaml = self.get_backup_dict()
        current_yaml = self.get_current_dict()
        not_found_keys = []
        for key, subkeys in self.keys_to_restore:
            if not subkeys and key not in backup_yaml:
                not_found_keys.append(key)
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
            raise Exception(
                "Not found values in backup for keys: {0}".format(
                    ",".join(not_found_keys)))
        old_path_name = "{0}.old".format(self.path)
        new_path_name = "{0}.new".format(self.path)
        shutil.copy(self.path, old_path_name)
        with open(new_path_name, "w") as new:
            yaml.safe_dump(current_yaml, new, default_flow_style=False)
        shutil.move(new_path_name, self.path)
        puppet.apply_tasks()
