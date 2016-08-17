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

import functools
import io
import itertools
import os
import shutil
import tarfile
import time

import six
from six.moves import urllib

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


def add_keys(node, gpg_keys_dir):
    cmd = ['apt-key', 'add', '-']
    with ssh_util.popen(cmd, stdin=ssh_util.PIPE, node=node) as proc:
        for filename in os.listdir(gpg_keys_dir):
            path = os.path.join(gpg_keys_dir, filename)
            if os.path.isfile(path):
                with open(path, 'rb') as f:
                    shutil.copyfileobj(f, proc.stdin)
        proc.stdin.close()


def download_packages_for_upgrade(node, packages):
    download_cmd = ['apt-get', '--yes', '--force-yes', '--download-only',
                    '--with-new-pkgs', 'upgrade'] + packages
    return ssh_util.call(download_cmd, node=node)


def _run_apt_get(mode, options, node, packages, fix_broken=False):
    if fix_broken:
        options.append('--fix-broken')
    opts = ' '.join(options)
    pkgs = ' '.join(packages)
    update_cmd = ['sh', '-c',
                  'DEBIAN_FRONTEND=noninteractive apt-get '
                  '--yes --force-yes {0} '
                  '-o Dpkg::Options::="--force-confdef" '
                  '-o Dpkg::Options::="--force-confold" '
                  '{1} {2}'.format(opts, mode, pkgs)]
    return ssh_util.call(update_cmd, node=node)


install_packages = functools.partial(_run_apt_get, 'install', [])
upgrade_packages = functools.partial(
    _run_apt_get, 'upgrade', ['--with-new-pkgs', '--show-upgraded'])
dist_upgrade_packages = functools.partial(
    _run_apt_get, 'dist-upgrade', ['--show-upgraded'])


def fetch_release_parameters(repo):
    url_release_part = "./{0}".format('/'.join(('dists', repo['suite'],
                                                'Release')))
    base_url = repo['uri']
    if not base_url.endswith('/'):
        base_url = "{0}/".format(repo['uri'])
    release_url = urllib.parse.urljoin(base_url, url_release_part)
    resp = urllib.request.urlopen(release_url)
    if resp.code != 200:
        raise UnavailableRelease(resp.code, release_url)
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
    filename = "etc/apt/sources.list.d/{0}.list".format(repo['name'])
    content = "{type} {uri} {suite} {section}".format(**repo)
    return filename, content


def create_repo_preferences(repo):
    filename = "etc/apt/preferences.d/{0}.pref".format(repo['name'])
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


def create_config_archive(archive_filename, repos):
    archive = tarfile.TarFile.open(archive_filename, 'w|gz')
    repos_with_prefs = (repo for repo in repos if repo['priority'])
    repos_configs = itertools.chain(
        six.moves.map(create_repo_source, repos),
        six.moves.map(create_repo_preferences, repos_with_prefs))
    nowtime = time.time()
    for filename, content in repos_configs:
        info = tarfile.TarInfo(name=filename)
        info.size = len(content)
        info.mtime = nowtime
        archive.addfile(info, fileobj=io.BytesIO(content))


def dpkg_remove(node, pkgs):
    ssh_util.call(['dpkg', '--force-depends', '--remove'] + pkgs, node=node)
