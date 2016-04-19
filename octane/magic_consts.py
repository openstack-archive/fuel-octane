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

PACKAGES = ["postgresql.x86_64", "pssh", "patch", "python-pip"]
PATCHES = [("nailgun", "/usr/lib/python2.6/site-packages/nailgun/extensions"
            "/cluster_upgrade/", "patches/nailgun-clone-ips.patch")]
# TODO: use pkg_resources for patches
CWD = os.path.dirname(__file__)  # FIXME

FUEL_CACHE = "/tmp"  # TODO: we shouldn't need this
PUPPET_DIR = "/etc/puppet/modules"
NAILGUN_ARCHIVATOR_PATCHES = [
    (
        "nailgun",
        os.path.join(PUPPET_DIR, "nailgun/manifests/"),
        os.path.join(CWD, "patches/timeout.patch")
    ),
]
BOOTSTRAP_INITRAMFS = "/var/www/nailgun/bootstrap/initramfs.img"

SSH_KEYS = ['/root/.ssh/id_rsa', '/root/.ssh/bootstrap.rsa']
OS_SERVICES = ["nova", "keystone", "heat", "neutron", "cinder", "glance"]
BRIDGES = ['br-ex', 'br-mgmt']
DEFAULT_DISKS = True
DEFAULT_NETS = True
ISCSI_CONFIG_PATH = "/etc/iscsi/initiatorname.iscsi"
VERSIONS = {
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

SYNC_CONTAINERS = []

RUNNING_REQUIRED_CONTAINERS = [
    "postgres",
    "rabbitmq",
    "keystone",
    "rsync",
    "astute",
    "rsyslog",
    "nailgun",
    "ostf",
    "nginx",
    "cobbler",
    "mcollective",
]

OPENSTACK_FIXTURES = \
    "/usr/lib/python2.6/site-packages/nailgun/fixtures/openstack.yaml"

MIRRORS_EXTRA_DIRS = ["ubuntu-full", "mos-ubuntu"]
