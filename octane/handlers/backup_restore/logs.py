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

from fuelclient import objects

from octane.handlers.backup_restore import base
from octane.util import fuel_client
from octane.util import helpers
from octane.util import subprocess


class LogsArchivator(base.Base):
    def backup(self):
        pass

    def restore(self):
        domain = helpers.get_astute_dict()["DNS_DOMAIN"]
        dirname = "/var/log/remote/"
        with fuel_client.set_auth_context(self.context):
            pairs = [(n.data["meta"]["system"]["fqdn"], n.data["ip"])
                     for n in objects.Node.get_all()]

        # bootstrap nodes not uniq and log creation not required
        pairs = [(f, i) for f, i in pairs if f != 'bootstrap']

        subprocess.call(["systemctl", "stop", "rsyslog"])
        try:
            for fqdn, ip_addr in pairs:
                if not fqdn.endswith(domain):
                    continue
                ip_addr_path = os.path.join(dirname, ip_addr)
                fqdn_path = os.path.join(dirname, fqdn)
                if os.path.islink(ip_addr_path):
                    continue
                if os.path.isdir(ip_addr_path):
                    os.rename(ip_addr_path, fqdn_path)
                else:
                    os.mkdir(fqdn_path)
                os.symlink(fqdn, ip_addr_path)
        finally:
            subprocess.call(["systemctl", "start", "rsyslog"])
