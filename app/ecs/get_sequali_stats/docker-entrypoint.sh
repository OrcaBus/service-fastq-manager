#!/usr/bin/env bash

# Set to fail
set -euo pipefail

# Globals
R1_PATH="/tmp/r1.fastq.gz"
R2_PATH="/tmp/r2.fastq.gz"
MAX_LINES="200000000"  # 50 million reads
OUTPUT_PATH="/tmp/sequali_output/output.json"

# Functions
echo_stderr(){
  echo "$(date -Iseconds): $1" 1>&2
}

download_gz_file(){
  local aws_s3_path="${1}"
  local local_tmp_path="${2}"
  local max_lines="${3}"
  (
    aws s3 cp \
      "${aws_s3_path}" \
      - 2>/dev/null || \
    true
  ) | \
  (
    unpigz \
      --stdout || \
    true
  ) | \
  head -n "${max_lines}" | \
  pigz \
    --stdout \
    --fast \
  > "${local_tmp_path}"
}

# ENVIRONMENT VARIABLES
# Inputs
if [[ ! -v R1_INPUT_URI ]]; then
  echo_stderr "Error! Expected env var 'R1_INPUT_URI' but was not found" 1>&2
  exit 1
fi

# Outputs
if [[ ! -v OUTPUT_URI ]]; then
  echo_stderr "Error! Expected env var 'OUTPUT_URI' but was not found" 1>&2
  exit 1
fi

# Download the file into standard unpigz decompression.
# We write out the first 200 million lines (50 million reads) to a temporary file
echo_stderr "Starting download of '${R1_INPUT_URI}'"
download_gz_file \
  "${R1_INPUT_URI}" \
  "${R1_PATH}" \
  "${MAX_LINES}"
echo_stderr "Finished download of '${R1_INPUT_URI}'"

# Check if R2_INPUT_URI is set and download to "${R2_PATH}"
if [[ -v R2_INPUT_URI ]]; then
  echo_stderr "Starting download of '${R2_INPUT_URI}'"
  download_gz_file \
	"${R2_INPUT_URI}" \
	"${R2_PATH}" \
	"${MAX_LINES}"
  echo_stderr "Finished download of '${R2_INPUT_URI}'"
fi

# Create a directory to store the output
mkdir -p "$(dirname "${OUTPUT_PATH}")"

# Import the reads into sequali
# Run through eval so that if R2_PATH does not exist, it is not parsed in as an empty argument
echo_stderr "Running Sequali stats"
eval uvx sequali \
  --outdir "$(dirname "${OUTPUT_PATH}")" \
  --json "$(basename "${OUTPUT_PATH}")" \
  "${R1_PATH}" \
  "${R2_PATH}" \
  1>log.txt 2>&1
has_error="$?"

if [[ "${has_error}" -ne 0 ]]; then
  echo_stderr "Error! Sequali failed with error code ${has_error}"
  echo_stderr "Sequali log:"
  cat log.txt 1>&2
  exit "${has_error}"
fi

# Summarise stats
echo_stderr "Summarising Sequali stats and uploading to S3"
python3 ./summarise_stats.py < "${OUTPUT_PATH}" | \
aws s3 cp - "${OUTPUT_URI}"
