#!/bin/bash -e

. /deploy/profile.sh

if [ -n "$http_proxy" ]; then
  git config --global http.proxy $http_proxy
fi

git config --global user.email "pullrequest@service"
git config --global user.name "pullrequest"

cd /opt/pullrequest/merge-service
execute python -u server.py \
  >>/opt/pullrequest/logs/merge-service.log 2>&1
echo "ERROR: merge-service is dead"
exit 1
