FROM fuel/cobbler_6.1
ADD resources/pmanager.py.patch /tmp/pmanager.py.patch
ADD resources/patch /usr/bin/
RUN patch -d /usr/lib/python2.6/site-packages/cobbler < /tmp/pmanager.py.patch
