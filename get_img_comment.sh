#!/bin/bash

if [ $# -ne 1 ]; then
	echo "Expected one argument: img/vid path." >&2
	exit 2
  # https://stackoverflow.com/questions/18568706/check-number-of-arguments-passed-to-a-bash-script
fi

# Validate input path
FILE_PATH="$(realpath "${1}")"
if [ -e "${FILE_PATH}" ]; then
  if [ -d "${FILE_PATH}" ]; then
	  echo "Input path ${1} not valid. Must be file, not directory." >&2
	  exit 2
	fi
else
  echo "Input file ${1} cannot be found." >&2
  exit 2
fi

SCRIPT_DIR="$(realpath "$(dirname "${0}")")"
# Temporarily switch working directory to script location to call python
cd "${SCRIPT_DIR}"
python3 <<< "import idevice_media_offload.date_compare as dc ; dc.get_comment('${FILE_PATH}', print_type=True)"
# https://unix.stackexchange.com/questions/533156/using-python-in-a-bash-script
PYTHON_RETURN=$? # gets return value of last command executed.

cd - > /dev/null # suppress outputs

# Make sure the program ran correctly
if [ ${PYTHON_RETURN} -ne 0 ]; then
	printf "\nSomething went wrong with the Python call.\n"
	exit 1
fi
