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
import urlparse

import fuelclient.objects as client_objects

from octane.handlers.backup_restore import base
from octane import magic_consts
from octane.util import env as env_util
from octane.util import helpers


class NaigunWWWBackup(base.PathArchivator):
    path = "/var/www/nailgun/"
    name = None

    def _get_values_list(self, data):
        raise NotImplementedError

    def _get_attributes(self):
        raise NotImplementedError

    def _get_mirrors(self):
        ipaddr = helpers.get_astute_dict()["ADMIN_NETWORK"]["ipaddress"]

        dirs_to_backup = set()
        for data in self._get_attributes():
            for value in self._get_values_list(data):
                if ipaddr in value['uri']:
                    path = urlparse.urlsplit(value['uri']).path
                    dir_name = path.lstrip("/").split('/', 1)[0]
                    dirs_to_backup.add(dir_name)
        return list(dirs_to_backup)

    def backup(self):
        for dir_name in self._get_mirrors():
            path = os.path.join(self.path, dir_name)
            self.archive.add(path, os.path.join(self.name, dir_name))


class MirrorsBackup(NaigunWWWBackup):
    name = "mirrors"

    def _get_attributes(self):
        for env in client_objects.Environment.get_all():
            yield env.get_attributes()

    def _get_values_list(self, data):
        return data['repo_setup']['repos']['value']


class RepoBackup(NaigunWWWBackup):
    name = "repos"

    def _get_attributes(self):
        for env in client_objects.Environment.get_all():
            yield env_util.get_generated(env.id)

    def _get_values_list(self, data):
        return data['provision']['image_data'].values()


class FullMirrorsBackup(NaigunWWWBackup):
    name = "mirrors"

    def _get_mirrors(self):
        releases = {r['version'] for r in client_objects.Release.get_all()}

        for dir_name in magic_consts.MIRRORS_EXTRA_DIRS:
            if os.path.exists(os.path.join(self.path, dir_name)):
                releases.add(dir_name)

        return releases


class FullRepoBackup(base.PathArchivator):
    name = 'repos/targetimages'
    path = '/var/www/nailgun/targetimages'
