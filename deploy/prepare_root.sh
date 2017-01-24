#!/bin/bash -e

id -u $APPUSER 2>/dev/null || {
  echo "Create user/group: $APPUSER:$APPGROUP ($APP_UID:$APP_GID) from ${APP_USERDIR}"
  execute groupadd --system -g $APP_GID $APPGROUP
  execute useradd --system -u $APP_UID -g $APPGROUP -d ${APP_USERDIR} -m -s /bin/bash -c "User" $APPUSER
}

[[ `id -u $APPUSER 2>/dev/null` = ${APP_UID} ]] || {
  echo "FATAL: User already exists with wrong ID";
  exit 1
}

execute chown $APPUSER:$APPGROUP $APP_USERDIR
[[ ! -d $APP_USERDIR/.ssh ]] || {
  set -x
  chown -R $APPUSER:$APPGROUP $APP_USERDIR/.ssh
  chmod 755 $APP_USERDIR/.ssh
  chmod 644 $APP_USERDIR/.ssh/*
  find $APP_USERDIR/.ssh/ \( -name "*rsa" -o -name "*key" \) -exec chmod 600 {} \;
  set +x
}

[[ ! -d $APP_USERDIR/repositories ]] || {
  execute chown -R $APPUSER:$APPGROUP $APP_USERDIR/repositories
}

cp -f /deploy/cron/crontab /etc/crontab
cp -f /deploy/logrotate/* /etc/logrotate.d/

[ ! -e /etc/nginx/conf.d/pullrequest_nginx.conf ] || rm /etc/nginx/conf.d/pullrequest_nginx.conf
execute /deploy/env_template.py /deploy/nginx/pullrequest_nginx.conf | tee /etc/nginx/conf.d/pullrequest_nginx.conf
[ ! -e /etc/nginx/sites-enabled/default ] || rm /etc/nginx/sites-enabled/default


[[ -d $APP_USERDIR/logs ]] || mkdir -p $APP_USERDIR/logs
execute chown $APPUSER:$APPGROUP $APP_USERDIR/logs
execute chmod 755 $APP_USERDIR/logs
