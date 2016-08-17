# -*- coding: utf-8 -*-

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

import pytest

from octane.util import apt

RELEASES = [
    """\
Origin: Mirantis
Label: mos9.0
Suite: mos9.0-updates
Codename: mos9.0-updates
MD5Sum: """,
    """\
Origin: Ubuntu
Label:Ubuntu
  Suite: vivid
Version: 15.04

Codename: vivid

SHA1:""",
    """\
SHA256:""",
]
PARAMS = [
    {'origin': 'Mirantis',
     'label': 'mos9.0',
     'codename': 'mos9.0-updates',
     'suite': 'mos9.0-updates'},
    {'origin': 'Ubuntu',
     'label': 'Ubuntu',
     'suite': 'vivid',
     'codename': 'vivid',
     'version': '15.04'},
]
REPOS = [
    {'uri': 'http://mirror.fuel-infra.org/mos-repos/ubuntu/9.0/',
     'suite': 'mos9.0-updates',
     'type': 'deb',
     'section': 'main',
     'name': 'mos-updates',
     'priority': 1050},
    {'uri': 'http://us.archive.ubuntu.com/ubuntu/',
     'suite': 'vivid',
     'type': 'deb-src',
     'section': 'main universe',
     'name': 'ubuntu',
     'priority': 601},
]


@pytest.mark.parametrize('repo,release,expected_params,url,code,is_error', [
    (REPOS[0], RELEASES[0], PARAMS[0],
     'http://mirror.fuel-infra.org/mos-repos/ubuntu/9.0/dists/'
     'mos9.0-updates/Release',
     200, False),
    (REPOS[1], RELEASES[1], PARAMS[1],
     'http://us.archive.ubuntu.com/ubuntu/dists/vivid/Release', 200, False),
    (REPOS[1], RELEASES[2], {},
     'http://us.archive.ubuntu.com/ubuntu/dists/vivid/Release', 200, False),
    ({'uri': 'https://example.com', 'suite': 'none'}, '', None,
     'https://example.com/dists/none/Release', 300, True),
    ({'uri': 'http://example.com/ubuntu', 'suite': 'trusty'}, '', None,
     'https://example.com/ubuntu/dists/none/Release', 300, True),
])
def test_fetch_release_parameters(mocker, repo, release, expected_params, url,
                                  code, is_error):
    mock_urlopen = mocker.patch('six.moves.urllib.request.urlopen')
    resp = mocker.MagicMock(code=code)
    resp.__iter__.return_value = iter(release.splitlines(True))
    mock_urlopen.return_value = resp

    if not is_error:
        params = apt.fetch_release_parameters(repo)
        mock_urlopen.assert_called_once_with(url)
        assert params == expected_params
    else:
        with pytest.raises(apt.UnavailableRelease):
            apt.fetch_release_parameters(repo)


@pytest.mark.parametrize('repo,filename,content', [
    (REPOS[0], 'etc/apt/sources.list.d/mos-updates.list',
     'deb http://mirror.fuel-infra.org/mos-repos/ubuntu/9.0/ mos9.0-updates '
     'main'),
    (REPOS[1], 'etc/apt/sources.list.d/ubuntu.list',
     'deb-src http://us.archive.ubuntu.com/ubuntu/ vivid main universe'),
])
def test_create_repo_source(repo, filename, content):
    result = apt.create_repo_source(repo)
    assert result[0] == filename
    assert result[1] == content


PREFERENCES = [
    """\
Package: *
Pin: release a=mos9.0-updates,o=Mirantis,n=mos9.0-updates,l=mos9.0,c=main
Pin-Priority: 1050""",
    """\
Package: *
Pin: release a=vivid,o=Ubuntu,n=vivid,l=Ubuntu,c=main,v=15.04
Pin-Priority: 601

Package: *
Pin: release a=vivid,o=Ubuntu,n=vivid,l=Ubuntu,c=universe,v=15.04
Pin-Priority: 601""",
]


@pytest.mark.parametrize('params,repo,filename,content', [
    (PARAMS[0], REPOS[0], 'etc/apt/preferences.d/mos-updates.pref',
     PREFERENCES[0]),
    (PARAMS[1], REPOS[1], 'etc/apt/preferences.d/ubuntu.pref', PREFERENCES[1]),
])
def test_create_repo_preferences(mocker, params, repo, filename, content):
    mock_fetch_release = mocker.patch(
        'octane.util.apt.fetch_release_parameters')
    mock_fetch_release.return_value = params
    result = apt.create_repo_preferences(repo)
    assert result[0] == filename
    assert result[1] == content
