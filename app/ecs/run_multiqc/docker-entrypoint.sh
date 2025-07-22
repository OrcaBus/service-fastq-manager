#!/usr/bin/env bash

set -euo pipefail

: '
Given the following env vars:
* DOWNLOAD_PARQUET_SCRIPT_URI
* NAMES_MAPPING_TSV_URI
* HTML_OUTPUT_URI

Perform the following steps:
1. Download the download parquet shell script from DOWNLOAD_PARQUET_SCRIPT_URI via a simple aws s3 cp command
2. Download the names mapping TSV file from NAMES_MAPPING_TSV_URI via a simple aws s3 cp command

3. Run the download parquet shell script, add in the --download-path to a temp directory

4. Run multiqc with the following options:
  --sample-names /path/to/names_mapping.tsv,
  <all parquet files each as a separate positional argument>
'

# Functions
echo_stderr() {
  echo "$@" >&2
}

# Check env vars are set
if [[ -z "${DOWNLOAD_PARQUET_SCRIPT_URI:-}" || -z "${NAMES_MAPPING_TSV_URI:-}" || -z "${HTML_OUTPUT_URI:-}" ]]; then
  echo_stderr "Required environment variables are not set."
  exit 1
fi

# Download the download parquet script
echo_stderr "Downloading download parquet script from ${DOWNLOAD_PARQUET_SCRIPT_URI}"
aws s3 cp "${DOWNLOAD_PARQUET_SCRIPT_URI}" /tmp/download_parquet.sh

# Download the names mapping TSV file
echo_stderr "Downloading names mapping TSV from ${NAMES_MAPPING_TSV_URI}"
aws s3 cp "${NAMES_MAPPING_TSV_URI}" /tmp/names_mapping.tsv

# Make the download parquet script executable
chmod +x /tmp/download_parquet.sh

# Create a temporary directory for downloads
DOWNLOAD_PATH="$(mktemp -d)"

# Run the download parquet script
echo_stderr "Running download parquet script with download path: ${DOWNLOAD_PATH}"
/tmp/download_parquet.sh "${DOWNLOAD_PATH}"

# Run multiqc with the names mapping and parquet files
echo_stderr "Running multiqc with sample names and parquet files"
uv run multiqc \
  --sample-names /tmp/names_mapping.tsv \
  --outdir "multiqc" \
  "${DOWNLOAD_PATH}/"

# Upload the multiqc report to the output URI
echo_stderr "Uploading multiqc report to ${HTML_OUTPUT_URI}"
aws s3 cp \
    --content-type "text/html" \
	"multiqc/multiqc_report.html" \
	"${HTML_OUTPUT_URI}"

# Upload the multiqc parquet file to the output URI
aws s3 cp \
	"multiqc/multiqc_data/BETA-multiqc.parquet" \
	"${PARQUET_OUTPUT_URI}"

# Clean up temporary files
rm -rf "${DOWNLOAD_PATH:-/tmp}/" /tmp/download_parquet.sh /tmp/names_mapping.tsv "multiqc/"
