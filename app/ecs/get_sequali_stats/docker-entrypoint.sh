#!/usr/bin/env bash

# Set to fail
set -euo pipefail

# Globals
if [[ ! -v LIBRARY_ID ]]; then
  echo "Error! Expected env var 'LIBRARY_ID' but was not found" 1>&2
  exit 1
fi

THREADS="8"  # Default number of threads

R1_PATH="/tmp/${LIBRARY_ID}_R1_001.fastq.gz"
R2_PATH="/tmp/${LIBRARY_ID}_R2_001.fastq.gz"
MAX_LINES="200000000"  # 50 million reads

# Sequali output paths
OUTPUT_SEQUALI_JSON_OUTPUT_DIR="/tmp/sequali_output"
OUTPUT_SEQUALI_JSON_OUTPUT_PATH="${OUTPUT_SEQUALI_JSON_OUTPUT_DIR}/output.json"
OUTPUT_SEQUALI_HTML_OUTPUT_PATH="${OUTPUT_SEQUALI_JSON_OUTPUT_DIR}/output.html"

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
mkdir -p "${OUTPUT_SEQUALI_JSON_OUTPUT_DIR}"

# Import the reads into sequali
# Run through eval so that if R2_PATH does not exist, it is not parsed in as an empty argument
echo_stderr "Running Sequali stats"
eval uv run sequali \
  --outdir "${OUTPUT_SEQUALI_JSON_OUTPUT_DIR}" \
  --json "$(basename "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}")" \
  --html "$(basename "${OUTPUT_SEQUALI_HTML_OUTPUT_PATH}")" \
  --threads "${THREADS}" \
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

# Manipulate the stats
if [[ -v READ_COUNT && -v BASE_COUNT_EST && "${READ_COUNT}" != "null" && "${BASE_COUNT_EST}" != "null" ]]; then
  echo_stderr "Setting read count to ${READ_COUNT} and base count to ${BASE_COUNT_EST} within sequali output json"
  mv "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}" "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}.bak"
  jq \
    --argjson readCount "${READ_COUNT}" \
    --argjson baseCountEst "${BASE_COUNT_EST}" \
    '
      ( if .summary.total_reads != 0 then ($readCount / .summary.total_reads) else 0.0 end ) as $readCountMultiplier |
      .summary += {
		"total_reads": $readCount,
		"total_bases": $baseCountEst,
		"q20_reads": (.summary.q20_reads * $readCountMultiplier),
		"q20_bases": (.summary.q20_bases * $readCountMultiplier),
		"total_gc_bases": (.summary.total_gc_bases * $readCountMultiplier),
		"total_n_bases": (.summary.total_n_bases * $readCountMultiplier),
	  } |
	  .summary_read2 += {
		"total_reads": $readCount,
		"total_bases": $baseCountEst,
		"q20_reads": (.summary_read2.q20_reads * $readCountMultiplier),
		"q20_bases": (.summary_read2.q20_bases * $readCountMultiplier),
		"total_gc_bases": (.summary_read2.total_gc_bases * $readCountMultiplier),
		"total_n_bases": (.summary_read2.total_n_bases * $readCountMultiplier),
	  }
    ' < "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}.bak" \
    > "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}"
fi

# Upload the Sequali HTML report to S3
aws s3 cp \
	--content-type 'text/html' \
	"${OUTPUT_SEQUALI_HTML_OUTPUT_PATH}" \
	"${OUTPUT_SEQUALI_HTML_URI}"

# Generate multiqc report
# We run it twice, once for the HTML report and once for the parquet file.
# For the parquet file, we need to replace the name with the fastq id,
# This means we have a unique id for each fastq id in the parquet bucket
mkdir -p multiqc_html
uv run multiqc \
	--outdir multiqc_html \
	"${OUTPUT_SEQUALI_JSON_OUTPUT_DIR}/"

# Upload the MultiQC HTML reports to S3
aws s3 cp \
	--content-type 'text/html' \
	"multiqc_html/multiqc_report.html" \
	"${OUTPUT_MULTIQC_HTML_URI}"

# Summarise stats
echo_stderr "Summarising Sequali stats and uploading to S3"
uv run python3 ./summarise_stats.py < "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}" | \
aws s3 cp - "${OUTPUT_SEQUALI_JSON_SUMMARY_URI}"

# Write out the parquet file to S3
uv run python3 ./json_to_parquet.py < "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}" | \
aws s3 cp - "${OUTPUT_SEQUALI_PARQUET_URI}"

# Now move onto the big-data stuff
# Re-edit the json to update the metadata to use the FASTQ ID instead of the library id in the filenames
# This allows us to have distinct names for each fastq-pair
# Since sequali is not recording instrument run id or lane information
# Now when we combine our fastq files, we can rename the fastq id to represent the library id
# Or whatever we want really
echo_stderr "Setting the library id in the filename to the FASTQ ID"
mv "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}" "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}.bak"
jq \
  --arg fastqId "${FASTQ_ID}" \
  --arg libraryId "${LIBRARY_ID}" \
  '
	.meta += {
      "filename": (.meta | .filename | gsub("\($libraryId)(?:_S[0-9+])?(?:_L[0-9]+)?"; $fastqId)),
      "filename_read2": (.meta | .filename_read2 | gsub("\($libraryId)(?:_S[0-9+])?(?:_L[0-9]+)?"; $fastqId))
	}
  ' < "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}.bak" \
  > "${OUTPUT_SEQUALI_JSON_OUTPUT_PATH}"

# Rerun the multiqc report using the edited filenames
mkdir -p multiqc_parquet
uv run multiqc \
	--outdir multiqc_parquet \
	"${OUTPUT_SEQUALI_JSON_OUTPUT_DIR}/"

aws s3 cp "multiqc_parquet/multiqc_data/BETA-multiqc.parquet" "${OUTPUT_MULTIQC_PARQUET_URI}"
