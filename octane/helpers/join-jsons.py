#!/bin/env python
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

import json
import sys


def join(a, b):
    t = {}
    for k, v in a.iteritems():
        nv = b.get(k)
        if nv is not None:
            if isinstance(v, basestring):
                t[k] = nv
            else:
                t[k] = join(v, nv)
        else:
            t[k] = v
    return t


if __name__ == '__main__':
    a = json.loads(sys.stdin.readline())
    b = json.loads(sys.stdin.readline())
    c = json.dumps(join(a, b))
    sys.stdout.write(c)
