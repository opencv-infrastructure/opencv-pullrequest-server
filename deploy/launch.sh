#!/bin/bash -e

. /deploy/profile.sh

git config --global user.email "pullrequest@service"
git config --global user.name "pullrequest"

cd /opt/pullrequest/merge-service
execute python -u server.py \
  >>/opt/pullrequest/logs/merge-service.log 2>&1
echo "ERROR: merge-service is dead"
exit 1
