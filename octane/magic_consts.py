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

import os.path

PATCHES = []
# TODO: use pkg_resources for patches
CWD = os.path.dirname(__file__)  # FIXME

FUEL_CACHE = "/tmp"  # TODO: we shouldn't need this
PUPPET_DIR = "/etc/puppet/modules"
NAILGUN_ARCHIVATOR_PATCHES = (
    PUPPET_DIR,
    os.path.join(CWD, "patches/timeout.patch"),
)
BOOTSTRAP_INITRAMFS = "/var/www/nailgun/bootstrap/initramfs.img"

PUPPET_TASKS_DIR = os.path.join(PUPPET_DIR, 'fuel/examples')
PUPPET_APPLY_TASKS_SCRIPT = os.path.join(PUPPET_TASKS_DIR, 'deploy.sh')

SSH_KEYS = ['/root/.ssh/id_rsa', '/root/.ssh/bootstrap.rsa']
OS_SERVICES = ["nova", "keystone", "heat", "neutron", "cinder", "glance"]
BRIDGES = ['br-ex', 'br-mgmt']
DEFAULT_DISKS = True
DEFAULT_NETS = True
ISCSI_CONFIG_PATH = "/etc/iscsi/initiatorname.iscsi"
VERSIONS = {
    '8.0': 'liberty',
    '7.0': 'kilo',
    '6.1': 'juno',
    '6.0': 'juno',
    '5.2.9': 'icehouse',
    '5.1.1': 'icehouse',
    '5.1': 'icehouse',
}

NAILGUN_URL = "http://127.0.0.1:8000"
KEYSTONE_API_URL = "http://127.0.0.1:5000/v2.0"
KEYSTONE_TENANT_NAME = "admin"

OPENSTACK_FIXTURES = "/usr/share/fuel-openstack-metadata/openstack.yaml"

OSD_REPOS_UPDATE = [
    # ("path", "content")
    (
        "/etc/apt/sources.list.d/mos.list",
        "deb http://{admin_ip}:8080/liberty-8.0/ubuntu/x86_64 "
        "mos8.0 main restricted"
    ),
    (
        "/etc/apt/sources.list.d/mos-updates.list",
        'deb http://{admin_ip}:8080/ubuntu/x86_64/ mos8.0 main restricted',
    ),
]
COBBLER_DROP_VERSION = "7.0"

MIRRORS_EXTRA_DIRS = ["ubuntu-full", "mos-ubuntu"]
RELEASE_STATUS_ENABLED = "available"
RELEASE_STATUS_MANAGED = "manageonly"

UPGRADE_NODE_PATCHES = [
    os.path.join(CWD, "patches/puppet/fix_mysql.patch")
]

BOOTSTRAP_UNSUPPORTED_IMAGES = ["centos"]
# NOTE(ogelbukh): it was agreed that 10MB is enough for config drive partition
CONFIGDRIVE_PART_SIZE = 10

NAILGUN_SERVICE_PATCHES = (
    "nailgun",
    "nailgun",
    "/usr/lib/python2.7/site-packages/nailgun/orchestrator/",
    os.path.join(CWD, "patches/nailgun_serializer.patch")
)
