FROM ubuntu:14.04

RUN \
  apt-get update && \
  apt-get install -y \
    git nginx python-virtualenv python-jinja2 \
    && \
  rm -rf /var/lib/apt/lists/* && \
  rm -f /etc/ssh/ssh_host_*

CMD ["/deploy/entry.sh"]
