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

import io
import os.path
import re
import shlex
import subprocess
import tarfile
import tempfile

from docker import Client


class IllegalArgumentError(ValueError):
    pass


class IllegalContainerName(ValueError):
    pass


class InvalidPatchFormat(IndexError):
    pass


class InvalidPatch(ValueError):
    pass

r = re.compile('^\+{3} ')
l = re.compile('[ \t]')


def extractFilesFromPatch(filePath):
    files = []

    if (filePath is None or not os.path.isfile(filePath)):
        raise InvalidPatch

    try:
        with open(filePath, "r") as f:
            for line in f:
                if (r.match(line)):
                    try:
                        fileName = l.split(line)
                        files.append(fileName[1])
                    except IndexError:
                        raise InvalidPatchFormat
    except IOError:
        raise InvalidPatch

    if (len(files) == 0):
        raise InvalidPatch

    return files


class DockerPatch(object):
    dockerClient = None
    containerId = None
    patches = {}

    def __init__(self, containerName):
        if (containerName is None):
            raise IllegalArgumentError("containerName must be not None")

        self.dockerClient = Client(
            base_url='unix://var/run/docker.sock', version='auto')
        for i in self.dockerClient.containers():
            if (i['Names'][0] == containerName):
                self.containerId = i['Id']
                break

        if (self.containerId is None):
            raise IllegalContainerName(
                "Container " + containerName + " not found")

    def addPatch(self, patchFile, prefix='/'):
        self.patches[patchFile] = {
            'prefix': prefix,
            'files': extractFilesFromPatch(patchFile),
            'patch': patchFile
        }

    def copy_from_docker(self, src, dest):
        reply = self.dockerClient.copy(self.containerId, src)
        filelike = io.BytesIO(reply.read())
        tar = tarfile.open(fileobj=filelike)
        file = tar.extractfile(os.path.basename(src))
        with open(dest, 'wb') as f:
            f.write(file.read())

        reply.release_conn()

    def apply(self):
        tempdir = tempfile.mkdtemp('patching')
        for p in self.patches.values():
            for f in p['files']:
                filePath = tempdir + '/' + f
                fileDir = os.path.dirname(filePath)

                if not os.path.exists(fileDir):
                    os.makedirs(fileDir)

                self.copy_from_docker(p['prefix'] + '/' + f, filePath)

                self.patchIt(p['patch'], tempdir)

    def patchIt(self, patchFile, tempdir):
        with open(patchFile, "r") as f:
            subprocess.Popen(shlex.split('patch -p0 -d ' + tempdir), stdin=f)
