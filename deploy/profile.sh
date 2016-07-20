. /deploy/env.sh
APP_USERDIR=${APP_USERDIR:-/home/$APPUSER}

tput() {
  /usr/bin/tput $* 2>/dev/null || true
}

RED=`tput setaf 1`
GREEN=`tput setaf 2`
YELLOW=`tput setaf 11`
RESET=`tput sgr0`

BOLD=`tput bold`

ERROR_STYLE=`tput setaf 15``tput setab 1`$BOLD

exec 9>&1

execute()
{
  echo $BOLD$YELLOW$*$RESET 1>&9
  [[ "$DRY_RUN" > 0 ]] || {
    $* || {
      RC=$?; echo "  "$ERROR_STYLE"result=$RC"$RESET 1>&9; exit $RC
    }
  }
}

error_exit() {
  echo $ERROR_STYLE$*$RESET 1>&9
  exit 1
}
