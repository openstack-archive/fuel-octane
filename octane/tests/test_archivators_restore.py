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
import mock
import os
import pytest
import random
import string


from octane.handlers.backup_restore import cobbler
from octane.handlers.backup_restore import fuel_keys
from octane.handlers.backup_restore import puppet
from octane.handlers.backup_restore import ssh
from octane.handlers.backup_restore import version


class TestMember(object):

    def __init__(self, name, is_file, is_extractable):
        self.name = name
        self.isfile = lambda: is_file
        self.is_extractable = is_extractable
        self.path = ''
        self.is_extracted = False
        self.dump = "".join(random.choice(string.letters + string.digits)
                            for _ in xrange(random.randint(10, 50)))

    def assert_exctract(self, path=None):
        assert self.is_extractable == self.is_extracted
        if self.is_extracted and path:
            assert os.path.join(path, "/") == os.path.join(self.path, "/")

    def read(self):
        return self.dump


class TestArchive(object):

    def __init__(self, members):
        self.members = members

    def __iter__(self):
        return iter(self.members)

    def extract(self, member, path):
        member.path = path
        member.is_extracted = True

    def extractfile(self, name):
        for m in self.members:
            if m.name == name:
                m.is_extracted = True
                return m


@pytest.mark.parametrize("cls,path,members", [
    (
        ssh.SshArchivator,
        "/root/.ssh/",
        [
            ("ssh/", False, False),
            ("ssh/k1y", True, True),
            ("ssh/k1y123", True, True),
            ("ssh_old/k1y123", True, False),
        ],
    ),
    (
        ssh.SshArchivator,
        "/root/.ssh/",
        [
            ("ssh/", False, False),
            ("ssh/k1y", True, True),
            ("ssh/k1y123", True, True),
            ("ssh_old/k1y123", True, False),
        ],
    ),
    (
        fuel_keys.FuelKeysArchivator,
        "/var/lib/fuel/keys",
        [
            ("fuel_keys/", False, False),
            ("fuel_keys/nginx.crt", True, True),
            ("fuel_keys/1/nginx.key", True, True),
        ],
    ),
    (
        puppet.PuppetArchivator, "/etc/puppet", [
            ("puppet/", False, False),
            ("puppet/some_dir", False, False),
            ("puppet/some_dir/file_1", True, True),
            ("puppet/some_dir_2/file_1", True, True),
            ("puppet_1/some_dir_2/file_1", True, False),
        ]
    ),
    (
        version.VersionArchivator, "/etc/fuel", [
            ("version/", False, False),
            ("version/some_dir", False, False),
            ("version/some_dir/file_1", True, True),
            ("version/some_dir_2/file_1", True, True),
            ("version_1/some_dir_2/file_1", True, False),
        ]
    ),
])
def test_path_restore(mocker, cls, path, members):
    members = [TestMember(n, f, e) for n, f, e in members]
    archive = TestArchive(members)
    cls(archive).restore()
    for member in members:
        member.assert_exctract(path)


@pytest.mark.parametrize("cls,path,container,members", [
    (
        cobbler.CobblerArchivator,
        "/var/lib/cobbler/config/systems.d/",
        "cobbler",
        [
            ("cobbler/file", True, True),
            ("cobbler/dir/file", True, True),
        ],
    ),
])
def test_container_archivator(mocker, cls, path, container, members):
    docker = mocker.patch("octane.util.docker.write_data_in_docker_file")
    members = [TestMember(n, f, e) for n, f, e in members]
    archive = TestArchive(members)
    cls(archive).restore()
    for member in members:
        member.assert_exctract()
        path_restor = member.name[len(container) + 1:]
        docker.assert_has_calls([
            mock.call(container, os.path.join(path, path_restor), member.dump)
        ])
