#!/bin/bash

# param 1 = source path to use (st videos dir)
# assumed to contain trailing slash
# param 2 = NAS st vid root
# param 3 = SSH port

JOB_NAME="$(basename "$1")" # Training Videos
ST_LOCAL_ROOT="$(dirname "$1")"

NAS_ST_DIR=$2
SSH_PORT=$3

TIMESTAMP="$(date "+%Y-%m-%dT%H%M%S")";
LOG_FILENAME=${ST_LOCAL_ROOT}/rsync_logs/${TIMESTAMP}_${JOB_NAME};
SRC_PATH="${1}"
DEST_PATH="${NAS_ST_DIR}"

printf "\n------------------------------------\n"
printf "\t-%s-\n\n" $JOB_NAME
printf "\t SRC: %s\n" ${SRC_PATH}
printf "\tDEST: %s\n\n" ${DEST_PATH}
rsync -rltgoD -zivh --log-file=${LOG_FILENAME} \
  --partial-dir=${ST_LOCAL_ROOT}/rsync_partials \
  -e "ssh -p ${SSH_PORT}" \
  ${SRC_PATH} ${DEST_PATH}
  # first group of options is equivalent to -a without the -p (permissions)
