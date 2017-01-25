#!/bin/bash -e
echo "Starting pullrequest container..."

. /deploy/profile.sh

if [ -f /.prepare_done ]; then
  echo "Preparation step is already completed. Remove deploy/.prepare_done to run it again"
else
  . /deploy/prepare_root.sh || exit 1
  su - $APPUSER -c /deploy/prepare.sh || exit 1
  touch /.prepare_done
fi

execute cron
execute /etc/init.d/nginx start
su - $APPUSER -c /deploy/launch.sh
echo "Application FAILED"
exit 1
