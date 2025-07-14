#!/usr/bin/env bash

# Set to fail
set -euo pipefail

# Functions
echo_stderr(){
  echo "$(date -Iseconds): $1" 1>&2
}

get_gz_raw_md5sum(){
  local aws_s3_path="${1}"
  aws s3 cp \
    "${aws_s3_path}" \
    - | \
  unpigz | \
  md5sum | \
  sed 's/ -//'
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

# Just use the standard aws s3 cp into unpigz to decompress the gzipped file
# Then pipe through wc -c to get the file size
md5sum="$( \
  get_gz_raw_md5sum \
    "${READ_INPUT_URI}" \
)"

# Write the file size to the output uri
aws s3 cp \
  - \
  "${OUTPUT_URI}" \
<<< "${md5sum}"
