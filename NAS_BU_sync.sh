#!/bin/bash

# param 1 = source path to use (Raw_Offload or Organized folder in iPhone or iPad BU root)
# assumed to contain trailing slash
# param 2 = NAS BU root
# param 3 = SSH port

if [[ $# -ne 3 ]]; then
  echo "Expected three arguments - source path, destination path, and SSH port." >&2
  exit 2
  # https://stackoverflow.com/questions/18568706/check-number-of-arguments-passed-to-a-bash-script
fi

JOB_NAME="$(basename "$1")" # Raw_Offload or Organized
SRC_BU_ROOT="$(dirname "$1")"
DEV="$(basename "$SRC_BU_ROOT")" # iPhone_Pictures or iPad_Pictures
NAS_BU_DATA=$2
SSH_PORT=$3

TIMESTAMP="$(date "+%Y-%m-%dT%H%M%S")";
LOG_FILENAME=${SRC_BU_ROOT}/rsync_logs/${TIMESTAMP}_${JOB_NAME};
SRC_PATH="${1}"
DEST_PATH="${NAS_BU_DATA}/${DEV}/${JOB_NAME}"

printf "\n${TIMESTAMP}\n"
printf -- "------------------------------------\n"
printf "\t-%s-\n\n" $JOB_NAME
printf "\t SRC: %s\n" ${SRC_PATH}
printf "\tDEST: %s\n\n" ${DEST_PATH}
rsync -rltgoD -zivh --log-file=${LOG_FILENAME} \
  --partial-dir=${SRC_BU_ROOT}/rsync_partials \
  -e "ssh -p ${SSH_PORT}" \
  ${SRC_PATH} ${DEST_PATH}
  # first group of options is equivalent to -a without the -p (permissions)
