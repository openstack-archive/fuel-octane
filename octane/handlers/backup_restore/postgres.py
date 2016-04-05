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
import logging
import os
import requests
import six
import urlparse
import yaml

from fuelclient.objects import node
from keystoneclient.v2_0 import Client as keystoneclient

from octane.handlers.backup_restore import base
from octane import magic_consts
from octane.util import fuel_client
from octane.util import helpers
from octane.util import patch
from octane.util import puppet
from octane.util import service
from octane.util import subprocess


LOG = logging.getLogger(__name__)


class PostgresArchivatorMeta(type):

    def __init__(cls, name, bases, attr):
        super(PostgresArchivatorMeta, cls).__init__(name, bases, attr)
        if cls.db is not None and cls.cmd is None:
            cls.cmd = ["sudo", "-u", "postgres", "pg_dump", "-C", cls.db]
        if cls.db is not None and cls.filename is None:
            cls.filename = "postgres/{0}.sql".format(cls.db)


@six.add_metaclass(PostgresArchivatorMeta)
class PostgresArchivator(base.CmdArchivator):
    db = None
    filename = None
    services = []

    def pre_restore(self):
        subprocess.call(["systemctl", "stop"] + self.services)
        subprocess.call(["sudo", "-u", "postgres", "dropdb", "--if-exists",
                         self.db])

    def restore(self):
        self.pre_restore()
        try:
            dump = self.archive.extractfile(self.filename)
            with subprocess.popen(["sudo", "-u", "postgres", "psql"],
                                  stdin=subprocess.PIPE) as process:
                process.stdin.write(dump.read())
        except Exception:
            LOG.exception("Failed to apply database restore for %s", self.db)
            self.revert()
            raise
        else:
            self.post_restore()

    def revert(self):
        pass

    def post_restore(self):
        puppet.apply(self.db)


class NailgunArchivator(PostgresArchivator):
    db = "nailgun"
    services = [
        "nailgun.service",
        "oswl_flavor_collectord.service",
        "oswl_image_collectord.service",
        "oswl_keystone_user_collectord.service",
        "oswl_tenant_collectord.service",
        "oswl_vm_collectord.service",
        "oswl_volume_collectord.service",
        "receiverd.service",
        "statsenderd.service",
        "assassind.service",
    ]
    patches = magic_consts.NAILGUN_ARCHIVATOR_PATCHES

    def pre_restore(self):
        super(NailgunArchivator, self).pre_restore()
        for args in self.patches:
            patch.patch_apply(*args)

    def revert(self):
        for args in self.patches:
            patch.apply_patches(*args, revert=True)
        subprocess.call(["systemctl", "restart"] + self.services)
        for service_name in self.services:
            service.wait_for_service(service_name)

    def post_restore(self):
        # NOTE(akscram): We need to remove the configuration file to
        #                trigger its creation and then db_sync.
        os.rename("/etc/nailgun/settings.yaml",
                  "/etc/nailgun/settings.yaml.back")
        super(NailgunArchivator, self).post_restore()
        self.revert()
        self.create_release()
        self.synchronize_deployment_tasks()
        self.create_links_on_remote_logs()

    def create_release(self):
        with open(magic_consts.OPENSTACK_FIXTURES, 'rb') as f:
            fixtures = yaml.load(f)
        base_release_fields = fixtures[0]['fields']
        for fixture in fixtures[1:]:
            release = helpers.merge_dicts(
                base_release_fields, fixture['fields'])
            self.__post_data_to_nailgun(
                "/api/v1/releases/",
                release,
                self.context.user,
                self.context.password)

    def __post_data_to_nailgun(self, url, data, user, password):
        ksclient = keystoneclient(
            auth_url=magic_consts.KEYSTONE_API_URL,
            username=user,
            password=password,
            tenant_name=magic_consts.KEYSTONE_TENANT_NAME,
        )
        resp = requests.post(
            urlparse.urljoin(magic_consts.NAILGUN_URL, url),
            json.dumps(data),
            headers={
                "X-Auth-Token": ksclient.auth_token,
                "Content-Type": "application/json",
            })
        LOG.debug(resp.content)
        return resp

    def synchronize_deployment_tasks(self):
        subprocess.call(
            [
                "fuel",
                "release",
                "--sync-deployment-tasks",
                "--dir",
                "/etc/puppet/",
            ],
            env=self.context.get_credentials_env())

        values = []
        for line in self._run_sql(
                "select id, generated from attributes;"):
            c_id, c_data = line.split("|", 1)
            data = json.loads(c_data)
            data["deployed_before"] = {"value": True}
            values.append("({0}, '{1}')".format(c_id, json.dumps(data)))

        if values:
            self._run_sql(
                'update attributes as a set generated = b.generated '
                'from (values {0}) as b(id, generated) '
                'where a.id = b.id;'.format(','.join(values))
            )

    def _run_sql(self, sql):
        sql_run_prams = [
            "sudo", "-u", "postgres", "psql", "nailgun", "--tuples-only", "-c"]
        result = subprocess.call_output(sql_run_prams + [sql])
        return result.strip().splitlines()

    def create_links_on_remote_logs(self):
        with open("/etc/fuel/astute.yaml") as astute:
            domain = yaml.load(astute)["DNS_DOMAIN"]
        dirname = "/var/log/remote/"
        with fuel_client.set_auth_context(self.context):
            pairs = [(n.data["meta"]["system"]["fqdn"], n.data["ip"])
                     for n in node.Node.get_all()]
        subprocess.call(["systemctl", "stop", "rsyslog.service"])
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
            subprocess.call(["systemctl", "start", "rsyslog.service"])
            service.wait_for_service("rsyslog.service")


class KeystoneArchivator(PostgresArchivator):
    db = "keystone"
    services = ["openstack-keystone.service"]
