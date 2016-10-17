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
PATCHES_DIR = os.path.join(CWD, "patches")

FUEL_CACHE = "/tmp"  # TODO: we shouldn't need this
PUPPET_DIR = "/etc/puppet/modules"
DEPLOYMENT_GRAPH_DIR = \
    "/var/www/nailgun/octane_code/puppet/octane_tasks/graphs"

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
# NOTE(akscram): This mapping contains environments versions and
# suitable upgrade_levels to support N+1 upgrades for Nova services.
UPGRADE_LEVELS = {
    '9.1': 'liberty',
    '9.0': 'liberty',
    '8.0': 'kilo',
    '7.0': 'juno',
    '6.1': 'icehouse',
    '6.0': 'icehouse',
    '5.2.9': 'havana',
    '5.1.1': 'havana',
    '5.1': 'havana',
}

NAILGUN_URL = "http://127.0.0.1:8000"
KEYSTONE_API_URL = "http://127.0.0.1:5000/v2.0"
KEYSTONE_TENANT_NAME = "admin"

OPENSTACK_FIXTURES = "/usr/share/fuel-openstack-metadata/openstack.yaml"


OSD_UPGRADE_REQUIRED_PACKAGES = [
    "libcephfs1", "librados2", "librbd1", "python-ceph", "python-cephfs",
    "python-rados", "python-rbd", "ceph", "ceph-common", "ceph-fs-common",
    "ceph-mds",
]

COBBLER_DROP_VERSION = "7.0"
CEPH_UPSTART_VERSION = "7.0"
NOVA_FLAVOR_DATA_MIGRATION_VERSION = "7.0"
CINDER_UPDATE_VOLUME_HOST_VERSION = "7.0"


MIRRORS_EXTRA_DIRS = ["ubuntu-full", "mos-ubuntu"]
RELEASE_STATUS_ENABLED = "available"
RELEASE_STATUS_MANAGED = "manageonly"

BOOTSTRAP_UNSUPPORTED_IMAGES = ["centos"]
# NOTE(ogelbukh): it was agreed that 10MB is enough for config drive partition
CONFIGDRIVE_PART_SIZE = 10

KEYSTONE_CONF = "/etc/keystone/keystone.conf"
KEYSTONE_PASTE = "/etc/keystone/keystone-paste.ini"
ACTIVE_IMG_PATH = "/var/www/nailgun/bootstraps/active_bootstrap/"

NOVA_PATCH_PREFIX_DIR = '/usr/lib/python2.7/dist-packages/'
NOVA_PATCHES = [
    os.path.join(CWD, "patches/nova.patch"),
]

SFTP_SERVER_BIN = '/usr/lib/sftp-server'

FUEL_KEYS_BASE_PATH = "/var/lib/fuel/keys"

KEYSTONE_PIPELINES = [
    "pipeline:public_api",
    "pipeline:admin_api",
    "pipeline:api_v3",
]

SKIP_CONTROLLER_TASKS = [
    "upload_cirros", "ceph_ready_check", "configure_default_route",
    "enable_rados",
]

COMPUTE_PREUPGRADE_PACKAGES = {
    'liberty-8.0': [
        "python-routes",
        "python-oslo.concurrency",
        "python-sqlparse",
        "nova-common",
        "python-pkg-resources",
        "python-oslo.policy",
        "neutron-plugin-ml2",
        "python-oslo.config",
        "python-glanceclient",
        "python-paramiko",
        "python-jinja2",
        "python-nova",
        "python-editor",
        "python-contextlib2",
        "python-oslo.serialization",
        "python-urllib3",
        "python-keystonemiddleware",
        "python-openssl",
        "fuel-ha-utils",
        "python-netaddr",
        "python-oslo.i18n",
        "python-cliff",
        "python-oslo.reports",
        "neutron-common",
        "python-oslo.versionedobjects",
        "python-oslo.db",
        "nailgun-mcagents",
        "python-novaclient",
        "python-unicodecsv",
        "neutron-plugin-openvswitch-agent",
        "python-oslo.rootwrap",
        "python-oslo.utils",
        "python-ipaddress",
        "python-oslo.lo",
        "python-msgpack",
        "python-amqp",
        "python-cryptography",
        "python-six",
        "python-oslo.context",
        "python-openvswitch",
        "python-netifaces",
        "network-checker",
        "python-oslo.messaging",
        "mcollective-common",
        "python-oslo.middleware",
        "python-jsonschema",
        "python-keystoneclient",
        "python-oslo.service",
        "python-neutronclient",
        "python-requests",
        "python-singledispatch",
        "python-neutron",
        "python-stevedore",
        "python-sqlalchemy",
        "nova-compute",
        "nova-compute-qemu",
        "python-extras",
        "mcollective",
        "python-cinderclient",
        "python-concurrent.futures",
    ]
}

ASTUTE_YAML = "/etc/fuel/astute.yaml"
CINDER_CONF = "/etc/cinder/cinder.conf"

CEPH_RELEASES = {'mitaka-9.0': 'hammer'}
