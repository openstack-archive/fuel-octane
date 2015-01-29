#!/bin/env python
import sys
import json


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
