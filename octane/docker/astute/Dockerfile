FROM fuel/astute_6.1
ADD resources/deploy_actions.rb.patch /tmp/deploy_actions.rb.patch
ADD resources/patch /usr/bin/
RUN patch -d /usr/lib64/ruby/gems/2.1.0/gems/astute-6.1.0/lib/astute < /tmp/deploy_actions.rb.patch
