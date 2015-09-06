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

import sys

from nailgun.db import db
from nailgun.extensions.volume_manager.models.node_volumes import NodeVolumes


node_id = int(sys.argv[1])
nv = db().query(NodeVolumes).filter(NodeVolumes.node_id == node_id).first()

os_vg = next(disk for disk in nv.volumes if 'id' in disk and
                                            disk['id'] == 'os')
nv.volumes = [disk for disk in nv.volumes if 'id' not in disk or
                                             disk['id'] != 'os']

for disk in nv.volumes:
    volumes = disk['volumes']
    disk['volumes'] = []
    for v in volumes:
        if v['type'] == 'pv' and v['vg'] == 'os' and v['size'] > 0:
            for vv in os_vg['volumes']:
                partition = {'name': vv['name'],
                             'size': vv['size'],
                             'type': 'partition',
                             'mount': vv['mount'],
                             'file_system': vv['file_system']}
                disk['volumes'].append(partition)
        else:
            if v['type'] == 'lvm_meta_pool' or v['type'] == 'boot':
                v['size'] = 0
            disk['volumes'].append(v)
nv.volumes.append({})
db.flush()
db.commit()
nv.volumes = nv.volumes[:-1]
db.flush()
db.commit()
