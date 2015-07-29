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
PATCHES = [
    ("cobbler", "/usr/lib/python2.6/site-packages/cobbler",
     "docker/cobbler/resources/pmanager.py.patch"),
    ("nailgun", "/usr/lib/python2.6/site-packages/nailgun/volumes",
     "docker/nailgun/resources/manager.py.patch"),
    ("nailgun", "/", "../octane_nailgun/tools/urls.py.patch"),
]
# TODO: use pkg_resources for patches
CWD = os.path.dirname(__file__)  # FIXME
FUEL_CACHE = "/tmp/octane/deployment"  # TODO: we shouldn't need this
PUPPET_DIR = "/etc/puppet/2014.2.2-6.1/modules"

SSH_KEYS = ['/root/.ssh/id_rsa', '/root/.ssh/bootstrap.rsa']
