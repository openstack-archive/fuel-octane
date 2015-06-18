FROM fuel/nailgun_6.1:latest
ENV OCTANE_WHEEL_VERSION 0.0.0
COPY dist/octane_nailgun-${OCTANE_WHEEL_VERSION}-py2-none-any.whl /root/
COPY tools/*.patch /root/
RUN pip install octane_nailgun-${OCTANE_WHEEL_VERSION}-py2-none-any.whl \
        && yum install -y patch \
        && cat /root/*.patch | patch -bNp1 -d /
