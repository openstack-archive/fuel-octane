FROM fuel/astute_6.1
ADD resources/deploy_actions.rb.patch /tmp/deploy_actions.rb.patch
ADD resources/patch /usr/bin/
RUN patch -d /usr/lib/python2.6/site-packages/nailgun/volumes/ < /tmp/deploy_actions.rb.patch
