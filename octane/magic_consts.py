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
PUPPET_DIR = "/etc/puppet/2015.1.0-7.0/modules"
BOOTSTRAP_INITRAMFS = "/var/www/nailgun/bootstrap/initramfs.img"

SSH_KEYS = ['/root/.ssh/id_rsa', '/root/.ssh/bootstrap.rsa']
OS_SERVICES = ["nova", "keystone", "heat", "neutron", "cinder", "glance"]
BRIDGES = ['br-ex', 'br-mgmt']
DEFAULT_DISKS = True
DEFAULT_NETS = True
ISCSI_CONFIG_PATH = "/etc/iscsi/initiatorname.iscsi"
