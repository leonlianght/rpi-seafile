FROM arm32v7/debian:9-slim

ARG VERSION
ENV SEAFILE_VERSION=${VERSION} SEAFILE_SERVER=seafile-server

COPY requirements.txt  /tmp/requirements.txt

WORKDIR /opt/seafile

COPY scripts /scripts

RUN apt update && \
    apt upgrade -y && \
    apt install -y --no-install-recommends python2.7 python-imaging python-pip python-wheel python-setuptools curl sqlite3 procps rsync && \
    pip install -r /tmp/requirements.txt && \
    rm -rf \
    /root/.cache \
    /root/.npm \
    /root/.pip \
    /usr/local/share/doc \
    /usr/share/doc \
    /usr/share/man \
    /var/cache/* \
    /var/lib/apt/lists/* \
    /var/log/* \
    /usr/share/info/* \
    /usr/share/linda/* \
    /usr/share/groff/* \
    /usr/share/lintian/overrides/* \
    /usr/share/omf/*/*-*.emf \
    /tmp/* && \
    mkdir -p /opt/seafile/ && \
    curl -sSL -o - https://github.com/haiwen/seafile-rpi/releases/download/v${SEAFILE_VERSION}/seafile-server_${SEAFILE_VERSION}_stable_pi.tar.gz  \
    | tar xzf - -C /opt/seafile/ && \
    python -m compileall -q /opt || : && \
    chmod +x /scripts/gc.sh && \
    groupadd -r -g 2500 seafile && \
    useradd -Mr seafile --uid 2500 -g seafile && \
    mkdir /shared /bootstrap /home/seafile /nginx && \
    chown -R seafile:seafile /shared /bootstrap /opt/seafile /home/seafile /nginx

USER seafile

CMD ["python", "/scripts/start.py"]

LABEL org.label-schema.name="Seafile server" \
      org.label-schema.version=${VERSION} \
      org.label-schema.docker.schema-version="1.0"
