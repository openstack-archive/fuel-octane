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
import shutil
import six
import urlparse
import yaml

from fuelclient.objects import node
from keystoneclient.v2_0 import Client as keystoneclient

from octane.handlers.backup_restore import base
from octane import magic_consts
from octane.util import docker
from octane.util import fuel_client
from octane.util import helpers
from octane.util import sql
from octane.util import subprocess


LOG = logging.getLogger(__name__)


class PostgresArchivatorMeta(type):

    def __init__(cls, name, bases, attr):
        super(PostgresArchivatorMeta, cls).__init__(name, bases, attr)
        cls.container = "postgres"
        if cls.db is not None and cls.cmd is None:
            cls.cmd = ["sudo", "-u", "postgres", "pg_dump", "-C", cls.db]
        if cls.db is not None and cls.filename is None:
            cls.filename = "postgres/{0}.sql".format(cls.db)


@six.add_metaclass(PostgresArchivatorMeta)
class PostgresArchivator(base.CmdArchivator):
    db = None

    def restore(self):
        dump = self.archive.extractfile(self.filename)
        subprocess.call([
            "systemctl", "stop", "docker-{0}.service".format(self.db)
        ])
        docker.stop_container(self.db)
        docker.run_in_container(
            "postgres",
            ["sudo", "-u", "postgres", "dropdb", "--if-exists", self.db],
        )
        with docker.in_container("postgres",
                                 ["sudo", "-u", "postgres", "psql"],
                                 stdin=subprocess.PIPE) as process:
            shutil.copyfileobj(dump, process.stdin)
        docker.start_container(self.db)
        docker.wait_for_container(self.db)
        subprocess.call([
            "systemctl", "start", "docker-{0}.service".format(self.db)
        ])


class NailgunArchivator(PostgresArchivator):
    db = "nailgun"
    select_admin_net_query = ("SELECT id FROM network_groups "
                              "WHERE name = 'fuelweb_admin'")
    set_admin_gateway_query = ("UPDATE network_groups SET gateway = '{0}' "
                               "WHERE id = '{1}' AND gateway = ''")
    set_admin_viptype_query = ("UPDATE ipaddrs SET vip_type = NULL "
                               "WHERE id = '{0}' AND vip_type = ''")

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

    def restore(self):
        for args in magic_consts.NAILGUN_ARCHIVATOR_PATCHES:
            docker.apply_patches(*args)
        try:
            super(NailgunArchivator, self).restore()
            self._post_restore_action()
            self._fix_admin_network()
        finally:
            for args in magic_consts.NAILGUN_ARCHIVATOR_PATCHES:
                docker.apply_patches(*args, revert=True)

    def _create_links_on_remote_logs(self):
        domain = helpers.get_astute_dict()["DNS_DOMAIN"]
        dirname = "/var/log/docker-logs/remote/"
        with fuel_client.set_auth_context(self.context):
            pairs = [(n.data["meta"]["system"]["fqdn"], n.data["ip"])
                     for n in node.Node.get_all()]
        docker.run_in_container("rsyslog", ["service", "rsyslog", "stop"])
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
            docker.run_in_container("rsyslog", ["service", "rsyslog", "start"])

    def _post_restore_action(self):
        data, _ = docker.run_in_container(
            "nailgun",
            ["cat", magic_consts.OPENSTACK_FIXTURES],
            stdout=subprocess.PIPE)
        fixtures = yaml.load(data)
        base_release_fields = fixtures[0]['fields']
        for fixture in fixtures[1:]:
            release = helpers.merge_dicts(
                base_release_fields, fixture['fields'])
            self.__post_data_to_nailgun(
                "/api/v1/releases/",
                release,
                self.context.user,
                self.context.password)
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
        for line in sql.run_psql_in_container(
                "select id, generated from attributes;", self.db):
            c_id, c_data = line.split("|", 1)
            data = json.loads(c_data)
            data["deployed_before"] = {"value": True}
            values.append("({0}, '{1}')".format(c_id, json.dumps(data)))

        if values:
            sql.run_psql_in_container(
                'update attributes as a set generated = b.generated '
                'from (values {0}) as b(id, generated) '
                'where a.id = b.id;'.format(','.join(values)),
                self.db)
        self._create_links_on_remote_logs()

    def _fix_admin_network(self):
        gateway = helpers.get_astute_dict()["ADMIN_NETWORK"]["ipaddress"]
        for net_id in sql.run_psql_in_container(self.select_admin_net_query,
                                                self.db):
            sql.run_psql_in_container(
                self.set_admin_gateway_query.format(gateway, net_id), self.db)
            sql.run_psql_in_container(
                self.set_admin_viptype_query.format(net_id), self.db)


class KeystoneArchivator(PostgresArchivator):
    db = "keystone"
