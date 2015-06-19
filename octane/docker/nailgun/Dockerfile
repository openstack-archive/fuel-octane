FROM fuel/nailgun_6.1
ADD resources/manager.py.patch /tmp/manager.py.patch
ADD resources/patch /usr/bin/
RUN patch -d /usr/lib/python2.6/site-packages/nailgun/volumes/ < /tmp/manager.py.patch
