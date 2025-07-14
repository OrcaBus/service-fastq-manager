#!/usr/bin/env bash

# Set to fail
set -euo pipefail

# Total reads
DEFAULT_MAX_READS=4000000

if [[ ! -v MAX_READS ]]; then
  # If MAX_READS is not set, use the default
  MAX_READS="${DEFAULT_MAX_READS}"
else
  # Ensure MAX_READS is a number
  if ! [[ "${MAX_READS}" =~ ^[0-9]+$ ]]; then
	echo "Error: MAX_READS must be a positive integer." 1>&2
	exit 1
  fi
fi

# Functions
echo_stderr(){
  echo "$(date -Iseconds): $1" 1>&2
}

get_gz_basecount_est(){
  # Only take every 2nd line of each of the 4 lines to get the read data
  # Then remove the 'N' character and count the characters
  local aws_s3_path="${1}"
  aws s3 cp \
    "${aws_s3_path}" \
    - | \
  zcat | \
  awk 'NR % 4 == 2' | \
  head -n "${MAX_READS}" | \
  sed 's/N//g' |
  wc -c
}

get_multiplier(){
  # If READ_COUNT is less than MAX_READS, then we just return 1
  local read_count="${1}"

if [[ "${read_count}" -lt "${MAX_READS}" ]]; then
	echo 1
  else
	# Otherwise, we calculate the multiplier as the ratio of READ_COUNT to MAX_READS
	python3 -c "print( ${read_count} / ${MAX_READS} )"
  fi
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

# Ensure we have a read count
if [[ ! -v READ_COUNT ]]; then
  echo_stderr "Error! Expected env var 'READ_COUNT' but was not found" 1>&2
  exit 1
fi

# Just use the standard aws s3 cp
# Then pipe through wc -c to get the file size
basecount_est="$( \
  get_gz_basecount_est \
	"${READ_INPUT_URI}" \
)"

# Get the multiplier based on the basecount estimate
multiplier="$( \
  get_multiplier \
	"${READ_COUNT}" \
)"

# Get the final estimate
basecount_est="$( \
  python3 -c "print( ${basecount_est} * ${multiplier} )" \
)"

# Write the file size to the output uri
aws s3 cp \
  - \
  "${OUTPUT_URI}" \
<<< "${basecount_est}"
