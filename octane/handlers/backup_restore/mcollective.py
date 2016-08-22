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
import json
import logging

from fuelclient import objects

from octane.handlers.backup_restore import base
from octane.util import fuel_client
from octane.util import mcollective
from octane.util import node as node_util

LOG = logging.getLogger(__name__)


class McollectiveArchivator(base.Base):
    filename = "mco/ping.json"

    def backup(self):
        status = mcollective.get_mco_ping_status()
        content = json.dumps(status)
        fileobj = io.BytesIO(content)
        tarinfo = self.archive.getattrinfo(archname=self.filename)
        self.archive.addfile(tarinfo, fileobj=fileobj)

    def restore(self):
        with fuel_client.set_auth_context(self.context):
            nodes = objects.Node.get_all()
            node_util.restart_mcollective(nodes)
        content = self.archive.extractfile(self.filename)
        if content is not None:
            orig_status = json.load(content)
            new_status = mcollective.get_mco_ping_status()
            offline = mcollective.compair_mco_ping_statuses(orig_status,
                                                            new_status)
            if offline:
                LOG.warning("Some nodes went offline after the upgrade of the "
                            "master node (check them manually): %s",
                            ", ".join(offline))
