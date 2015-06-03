from docker import Client
from docker import errors
from os import makedirs, path

import re
import tempfile
from shutil import copyfileobj
import tarfile
import io
import subprocess


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

    if (filePath is None or not path.isfile(filePath)):
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


class DockerPatch():
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
        file = tar.extractfile(path.basename(src))
        with open(dest, 'wb') as f:
            f.write(file.read())

        reply.release_conn()

    def apply(self):
        tempdir = tempfile.mkdtemp('patching')
        for p in self.patches.values():
            for f in p['files']:
                filePath = tempdir + '/' + f
                fileDir = path.dirname(filePath)

                if not path.exists(fileDir):
                    makedirs(fileDir)

                self.copy_from_docker(p['prefix'] + '/' + f, filePath)

                self.patchIt(p['patch'], tempdir)

    def patchIt(self, patchFile, tempdir):
        with open(patchFile, "r") as f:
            outputStream = subprocess.Popen(
                shlex.split('patch -p0 -d ' + tempdir), stdin=f)
