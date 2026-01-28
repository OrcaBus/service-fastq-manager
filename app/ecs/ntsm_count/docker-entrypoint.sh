#!/usr/bin/env bash

# Set to fail
set -euo pipefail

# Set python3 version
hash -p /usr/bin/python3.12 python3

# Globals
R1_PATH="/tmp/r1.fastq.gz"
R2_PATH="/tmp/r2.fastq.gz"
OUTPUT_NTSM_PATH="/tmp/output.ntsm"
MAX_LINES="128000000"  # 48 million reads ~ 3x coverage

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
    true \
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

if [[ ! -v R2_INPUT_URI ]]; then
  echo_stderr "Error! Expected env var 'R2_INPUT_URI' but was not found" 1>&2
  exit 1
fi

if [[ ! -v NTSM_FASTA_PATH ]]; then
  echo_stderr "Error! Expected env var 'NTSM_FASTA_PATH' but was not found" 1>&2
  exit 1
fi

# Ensure we have an output uri
if [[ ! -v OUTPUT_URI ]]; then
  echo_stderr "Error! Expected env var 'OUTPUT_URI' but was not found" 1>&2
  exit 1
fi

# Download the file through standard unpigz decompression.
# We write out the first 72 million lines (18 million reads) to a temporary file
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

# Run ntsm count
# Run through eval so that if R2_PATH is not set, it will be parsed in as an empty argument
echo_stderr 'Running ntsmCount binary on the subsetted fastq files'
eval ntsmCount \
  --threads "${NTSM_THREADS-1}" \
  --snp "${NTSM_FASTA_PATH}" \
  --output "${OUTPUT_NTSM_PATH%.ntsm}.summary.txt" \
  "${R1_PATH}" \
  "${R2_PATH-}" > "${OUTPUT_NTSM_PATH}"
echo_stderr 'ntsmCount complete'

# Upload the outputs to s3
# Upload the output to s3
echo_stderr 'Uploading summary and fingerprint files to s3'
aws s3 cp \
  --sse="AES256" \
  "${OUTPUT_NTSM_PATH%.ntsm}.summary.txt" \
  "${OUTPUT_URI%.ntsm}.summary.txt"

aws s3 cp \
  --sse="AES256" \
  "${OUTPUT_NTSM_PATH}" \
  "${OUTPUT_URI}"
