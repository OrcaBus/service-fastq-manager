#!/usr/bin/env bash

# Set to fail
set -euo pipefail

# Functions
echo_stderr(){
  echo "$(date -Iseconds): $1" 1>&2
}

get_gz_line_count(){
  local aws_s3_path="${1}"
  aws s3 cp \
    "${aws_s3_path}" \
    - | \
  unpigz | \
  wc -l
}

# ENVIRONMENT VARIABLES
# Inputs
if [[ ! -v READ_INPUT_URI ]]; then
  echo_stderr "Error! Expected env var 'READ_INPUT_URI' but was not found" 1>&2
  exit 1
fi

# Ensure we have an output uri
if [[ ! -v OUTPUT_URI ]]; then
  echo_stderr "Error! Expected env var 'OUTPUT_URI' but was not found" 1>&2
  exit 1
fi

# Just use the standard aws s3 cp
# Then pipe through wc -c to get the file size
line_count="$( \
  get_gz_line_count \
    "${READ_INPUT_URI}" \
)"

# Fastqs are 4 lines per read, so divide by 4
read_count="$(( line_count / 4 ))"

# Write the file size to the output uri
aws s3 cp \
  - \
  "${OUTPUT_URI}" \
<<< "${read_count}"
