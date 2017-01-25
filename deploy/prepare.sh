#!/bin/bash -e

. /deploy/profile.sh

cp -r /etc/skel/. ${HOME}

if [ ! -f ~/.ssh/config ]; then
  error_exit "SSH config missing"
fi
chmod 644 ${HOME}/.ssh/config


(
echo "Updating repositories..."
cd /opt/pullrequest/repositories

update_repo() {
  DIR=$1
  FETCH_URL=$2
  PUSH_URL=$3
  CLONE_URL=${4:-$FETCH_URL}
  [[ -d $DIR ]] || git clone $CLONE_URL $DIR
  (
    cd $DIR
    git config remote.upstream.url >/dev/null || \
      git remote add upstream $FETCH_URL
    git remote set-url upstream $FETCH_URL
    git remote set-url --push upstream $PUSH_URL
  ) || error_exit "FATAL: Can't update repo: $DIR"
}

# Note: github.com-push is defined in ~/.ssh/config
OPENCV_GIT_URL=${OPENCV_GIT_URL:-https://github.com/opencv}
update_repo opencv https://github.com/opencv/opencv.git ssh://github.com-push/opencv/opencv.git ${OPENCV_GIT_URL}/opencv.git
update_repo opencv_extra https://github.com/opencv/opencv_extra.git ssh://github.com-push/opencv/opencv_extra.git ${OPENCV_GIT_URL}/opencv_extra.git
update_repo opencv_contrib https://github.com/opencv/opencv_contrib.git ssh://github.com-push/opencv/opencv_contrib.git ${OPENCV_GIT_URL}/opencv_contrib.git

) || error_exit "FATAL: Can't update repositories"
