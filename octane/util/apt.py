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

import requests
from urlparse import urljoin

from octane.util import ssh as ssh_util

PREFERENCES = [
    ('suite', 'a'),
    ('origin', 'o'),
    ('codename', 'n'),
    ('label', 'l'),
    ('component', 'c'),
    ('version', 'v'),
]


class UnavailableRelease(Exception):
    message = "Unexpected response status {0} for URL {1}."

    def __init__(self, status, url):
        super(UnavailableRelease, self).__init__(self.message.format(
            status, url))


def upgrade_packages(node, packages):
    if not packages:
        raise Exception(
            "There are not packages for the selected release."
        )
    pkgs = ' '.join(packages)
    update_cmd = ['sh', '-c',
                  'DEBIAN_FRONTEND=noninteractive apt-get '
                  'install --only-upgrade --yes --force-yes '
                  '-o Dpkg::Options::="--force-confdef" '
                  '-o Dpkg::Options::="--force-confold" '
                  '{0}'.format(pkgs)]
    return ssh_util.call(update_cmd, node=node)


def fetch_release_parameters(repo):
    url_release_part = "./{0}".format('/'.join(('dists', repo['suite'],
                                                'Release')))
    base_url = repo['uri']
    if not base_url.endswith('/'):
        base_url = "{0}/".format(repo['uri'])
    release_url = urljoin(base_url, url_release_part)
    resp = requests.get(release_url)
    if resp.status_code != 200:
        raise UnavailableRelease(resp.status_code, release_url)
    params = {}
    for line in resp:
        key, _, value = line.partition(':')
        key = key.strip().lower()
        value = value.strip()
        if not key or not value:
            continue
        # NOTE(akscram): Normal Release files contain meaningful fields
        #                at the beginning.
        if key in ('md5sum', 'sha1', 'sha256'):
            break
        params[key] = value
    return params


def create_repo_source(repo):
    filename = "/etc/apt/sources.list.d/{0}.list".format(repo['name'])
    content = "{type} {uri} {suite} {section}".format(**repo)
    return filename, content


def create_repo_preferences(repo):
    filename = "/etc/apt/preferences.d/{0}.pref".format(repo['name'])
    release_params = fetch_release_parameters(repo)
    content = []
    components = repo['section'].split()
    for component in components:
        params = dict(release_params, component=component)
        release = ','.join("{0}={1}".format(key, params[name])
                           for name, key in PREFERENCES
                           if name in params)
        content.append(
            "Package: *\n"
            "Pin: release {release}\n"
            "Pin-Priority: {priority}"
            .format(release=release, priority=repo['priority']))
    return filename, '\n\n'.join(content)
