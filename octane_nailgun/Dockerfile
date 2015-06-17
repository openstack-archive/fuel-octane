FROM fuel/nailgun_6.1:latest
COPY dist/octane_nailgun-*-py2-none-any.whl /root/
COPY tools/*.patch /root/
RUN pip install octane_nailgun-*-py2-none-any.whl && \
    yum install -y patch && \
    patch -bNp1 -d / <(cat /root/*.patch)
