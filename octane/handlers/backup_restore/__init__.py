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

from octane.handlers.backup_restore import astute
from octane.handlers.backup_restore import cobbler
from octane.handlers.backup_restore import fuel_keys
from octane.handlers.backup_restore import fuel_uuid
# from octane.handlers.backup_restore import logs
from octane.handlers.backup_restore import mirrors
from octane.handlers.backup_restore import nailgun_plugins
# from octane.handlers.backup_restore import postgres
from octane.handlers.backup_restore import puppet
# from octane.handlers.backup_restore import release
from octane.handlers.backup_restore import ssh
from octane.handlers.backup_restore import version


# NOTE(akscram): Unsupported archivators are disabled and will be
# re-wrote one-by-one. Docker containers were removed in 9.0 and all
# services are run now in OS on the host. This major change requires to
# modify current archivators that use containers.
ARCHIVATORS = [
    astute.AstuteArchivator,
    # SSH restore must go before Cobbler restore so it updates
    # /etc/cobbler/authorized_keys file automatically
    ssh.SshArchivator,
    cobbler.CobblerArchivator,
    fuel_keys.FuelKeysArchivator,
    fuel_uuid.FuelUUIDArchivator,
    puppet.PuppetArchivator,
    # postgres.KeystoneArchivator,
    # Nailgun restore should be after puppet restore
    # postgres.NailgunArchivator,
    # release.ReleaseArchivator,
    # logs.LogsArchivator,
    version.VersionArchivator,
    nailgun_plugins.NailgunPluginsArchivator,
    # puppet.PuppetApplyHost,
]

REPO_ARCHIVATORS = [
    mirrors.MirrorsBackup,
    mirrors.RepoBackup,
]

FULL_REPO_ARCHIVATORS = [
    mirrors.FullMirrorsBackup,
    mirrors.FullRepoBackup,
]


class NailgunCredentialsContext(object):

    def __init__(self, user, password):
        self.user = user
        self.password = password

    def get_credentials_env(self):
        env = os.environ.copy()
        env["OS_USERNAME"] = self.user
        env["OS_PASSWORD"] = self.password
        return env
