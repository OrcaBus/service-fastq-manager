#!/usr/bin/env bash

# Set to fail
set -euo pipefail

: '
Derive insertSizeEstimate from Picard CollectInsertSizeMetrics.

Sequali cannot observe an insert size larger than the read-pair length, so the
value it reports is capped. Instead we align a small fixed sample of reads to
the full hg38 reference (no masking) and run Picard CollectInsertSizeMetrics to
obtain a MEDIAN_INSERT_SIZE that is not bounded by read length.

Flow:
1. Download the reference fasta (+ .fai index).
2. Download R1 (and R2 if set); for gzip inputs, decompress directly and
   truncate to MAX_PICARD_READS reads (the gzip-path 10K cap guarantee).
3. Align with `minimap2 -ax sr` to the full hg38 reference (no masking) with a
   read group.
4. Filter with `samtools view -f 0x2 -F 0x900` (properly paired, exclude
   secondary + supplementary) plus optional --min-MQ; coordinate sort + index.
5. Run Picard CollectInsertSizeMetrics -> text metrics + histogram PDF.
6. Run MultiQC over the Picard output dir -> HTML report + parquet.
7. Convert the Picard metrics text to parquet via metrics_to_parquet.py.
8. Read MEDIAN_INSERT_SIZE from that parquet and write
   { "insertSizeEstimate": <value> } JSON.
9. Upload PDF / picard parquet / MultiQC HTML / MultiQC parquet / summary JSON.
'

# Functions
echo_stderr(){
  echo "$(date -Iseconds): $1" 1>&2
}

download_gz_file(){
  local aws_s3_path="${1}"
  local local_tmp_path="${2}"
  aws s3 cp \
    --quiet \
    "${aws_s3_path}" \
    "${local_tmp_path}"
}

# Standard parameters
MINIMAP_THREADS="8"
SAMTOOLS_THREADS="8"

# Check binaries
BINARIES_LIST=( \
  "minimap2" \
  "samtools" \
  "aws" \
  "picard" \
  "pigz" \
  "uv" \
)

for binary_iter in "${BINARIES_LIST[@]}"; do
  if ! command -v "${binary_iter}" &> /dev/null; then
    echo_stderr "Could not find ${binary_iter} binary, exiting"
    exit 1
  fi
done

# ENVIRONMENT VARIABLES
# Identity
if [[ ! -v FASTQ_ID ]]; then
  echo_stderr "Error! Expected env var 'FASTQ_ID' but was not found"
  exit 1
fi

if [[ ! -v LIBRARY_ID ]]; then
  echo_stderr "Error! Expected env var 'LIBRARY_ID' but was not found"
  exit 1
fi

# Inputs
if [[ ! -v R1_INPUT_URI ]]; then
  echo_stderr "Error! Expected env var 'R1_INPUT_URI' but was not found"
  exit 1
fi

if [[ ! -v REF_GENOME_URI ]]; then
  echo_stderr "Error! Expected env var 'REF_GENOME_URI' but was not found"
  exit 1
fi

if [[ ! -v MAX_PICARD_READS ]]; then
  echo_stderr "Error! Expected env var 'MAX_PICARD_READS' but was not found"
  exit 1
fi

# Outputs
if [[ ! -v OUTPUT_PICARD_PARQUET_URI ]]; then
  echo_stderr "Error! Expected env var 'OUTPUT_PICARD_PARQUET_URI' but was not found"
  exit 1
fi

if [[ ! -v OUTPUT_PICARD_PDF_URI ]]; then
  echo_stderr "Error! Expected env var 'OUTPUT_PICARD_PDF_URI' but was not found"
  exit 1
fi

if [[ ! -v OUTPUT_MULTIQC_HTML_URI ]]; then
  echo_stderr "Error! Expected env var 'OUTPUT_MULTIQC_HTML_URI' but was not found"
  exit 1
fi

if [[ ! -v OUTPUT_MULTIQC_PARQUET_URI ]]; then
  echo_stderr "Error! Expected env var 'OUTPUT_MULTIQC_PARQUET_URI' but was not found"
  exit 1
fi

if [[ ! -v OUTPUT_INSERT_SIZE_ESTIMATE_URI ]]; then
  echo_stderr "Error! Expected env var 'OUTPUT_INSERT_SIZE_ESTIMATE_URI' but was not found"
  exit 1
fi

# Set reference genome vars
REF_GENOME_PATH="/tmp/$(basename "${REF_GENOME_URI}")"

# Set fastq input vars
# Raw gzip downloads (as provided, either straight from filemanager or already
# decompressed by the ORA service into gzip)
R1_GZIP_PATH="/tmp/${LIBRARY_ID}_R1_001.fastq.gz"
R2_GZIP_PATH="/tmp/${LIBRARY_ID}_R2_001.fastq.gz"
# Truncated (first MAX_PICARD_READS reads) fastqs fed to minimap2
R1_TRUNCATED_PATH="/tmp/${LIBRARY_ID}_R1_001.truncated.fastq"
R2_TRUNCATED_PATH="/tmp/${LIBRARY_ID}_R2_001.truncated.fastq"

# Set alignment / picard vars.
# Name the BAM after the FASTQ_ID: Picard records the input basename in the
# metrics header, and MultiQC derives the sample name from that. Naming it here
# makes the MultiQC sample name (in both the HTML report and the parquet) the
# FASTQ_ID rather than a generic 'sorted.filtered'.
SORTED_FILTERED_BAM="/tmp/${FASTQ_ID}.bam"
PICARD_OUTPUT_DIR="/tmp/picard_output"
PICARD_METRICS_TXT="${PICARD_OUTPUT_DIR}/insert_size_metrics.txt"
PICARD_HISTOGRAM_PDF="${PICARD_OUTPUT_DIR}/insert_size_histogram.pdf"
PICARD_METRICS_PARQUET="${PICARD_OUTPUT_DIR}/insert_size_metrics.parquet"

# Fastq truncation is expressed in lines (4 lines per read)
TRUNCATE_LINES="$(( MAX_PICARD_READS * 4 ))"

# Download the reference genome (+ .fai index), mirroring tiny_alignment
echo_stderr "Downloading reference genome '${REF_GENOME_URI}'"
download_gz_file \
  "${REF_GENOME_URI}" \
  "${REF_GENOME_PATH}"
download_gz_file \
  "${REF_GENOME_URI}.fai" \
  "${REF_GENOME_PATH}.fai"

# Download R1
echo_stderr "Starting download of '${R1_INPUT_URI}'"
download_gz_file \
  "${R1_INPUT_URI}" \
  "${R1_GZIP_PATH}"
echo_stderr "Finished download of '${R1_INPUT_URI}'"

# Decompress + truncate R1 to the first MAX_PICARD_READS reads.
# This truncation is the gzip-path guarantee of the fixed read cap.
echo_stderr "Truncating R1 to the first ${MAX_PICARD_READS} reads"
pigz --decompress --stdout "${R1_GZIP_PATH}" | \
head -n "${TRUNCATE_LINES}" \
  > "${R1_TRUNCATED_PATH}"

# Download R2 if provided and truncate the same way
HAS_R2="false"
if [[ -v R2_INPUT_URI ]]; then
  HAS_R2="true"
  echo_stderr "Starting download of '${R2_INPUT_URI}'"
  download_gz_file \
    "${R2_INPUT_URI}" \
    "${R2_GZIP_PATH}"
  echo_stderr "Finished download of '${R2_INPUT_URI}'"

  echo_stderr "Truncating R2 to the first ${MAX_PICARD_READS} reads"
  pigz --decompress --stdout "${R2_GZIP_PATH}" | \
  head -n "${TRUNCATE_LINES}" \
    > "${R2_TRUNCATED_PATH}"
fi

# Align with minimap2 to the FULL hg38 reference (no masking), attach a read
# group keyed on the fastq id (fall back to the library id), filter to
# properly-paired reads while excluding secondary (0x100) + supplementary (0x800)
# = 0x900 alignments, optionally apply a MAPQ threshold, then coordinate sort +
# index.
RG_SAMPLE="${FASTQ_ID:-${LIBRARY_ID}}"

# Build the samtools view args as an array so the optional --min-MQ flag is only
# passed when MIN_MAPPING_QUALITY is set and non-empty.
SAMTOOLS_VIEW_ARGS=( \
  "--uncompressed" \
  "--require-flags" "0x2" \
  "--exclude-flags" "0x900" \
)
if [[ -v MIN_MAPPING_QUALITY && -n "${MIN_MAPPING_QUALITY}" ]]; then
  echo_stderr "Applying minimum mapping quality filter of '${MIN_MAPPING_QUALITY}'"
  SAMTOOLS_VIEW_ARGS+=( "--min-MQ" "${MIN_MAPPING_QUALITY}" )
fi

# Assemble the minimap2 read inputs (R2 only when present)
MINIMAP_READ_INPUTS=( "${R1_TRUNCATED_PATH}" )
if [[ "${HAS_R2}" == "true" ]]; then
  MINIMAP_READ_INPUTS+=( "${R2_TRUNCATED_PATH}" )
fi

echo_stderr "Aligning reads to the full reference genome with minimap2"
minimap2 \
  -ax sr \
  -v1 \
  -t "${MINIMAP_THREADS}" \
  -R "@RG\tID:${RG_SAMPLE}\tSM:${RG_SAMPLE}" \
  "${REF_GENOME_PATH}" \
  "${MINIMAP_READ_INPUTS[@]}" | \
samtools view \
  "${SAMTOOLS_VIEW_ARGS[@]}" \
  - | \
samtools sort \
  --output-fmt BAM \
  --threads "${SAMTOOLS_THREADS}" \
  -o "${SORTED_FILTERED_BAM}##idx##${SORTED_FILTERED_BAM}.bai" \
  --write-index \
  -

# Run Picard CollectInsertSizeMetrics to produce the text metrics file and the
# insert-size histogram PDF.
#
# --MINIMUM_PCT 0: by default Picard discards any read-orientation category
# holding < 5% of the aligned pairs. On our small fixed sample (~10k reads) this
# can discard every category, producing no metrics file at all ("All data
# categories were discarded because they contained < 0.05 ..."). Setting it to 0
# keeps all pairs so the metrics are always emitted.
#
# Note: the "Unable to load libgkl_compression.so ... can't load AMD 64 .so on a
# AARCH64 platform" line is a benign WARN - it is Intel's x86-only GKL native
# acceleration library. Picard is a JVM tool and runs fine on arm64, falling back
# to pure-Java (de)compression.
mkdir -p "${PICARD_OUTPUT_DIR}"
echo_stderr "Running Picard CollectInsertSizeMetrics"
picard CollectInsertSizeMetrics \
  --INPUT "${SORTED_FILTERED_BAM}" \
  --OUTPUT "${PICARD_METRICS_TXT}" \
  --Histogram_FILE "${PICARD_HISTOGRAM_PDF}" \
  --REFERENCE_SEQUENCE "${REF_GENOME_PATH}" \
  --MINIMUM_PCT 0

# Fail loudly if Picard produced no metrics file (e.g. no aligned pairs at all)
# rather than surfacing a confusing downstream "cannot stat" error.
if [[ ! -s "${PICARD_METRICS_TXT}" ]]; then
  echo_stderr "Error! Picard did not produce a metrics file at '${PICARD_METRICS_TXT}'."
  echo_stderr "This usually means too few reads aligned as proper pairs."
  exit 1
fi

# Run MultiQC over the Picard output directory.
# The MultiQC sample name is derived from the Picard --INPUT basename recorded
# in the metrics header, which is our BAM named "${FASTQ_ID}.bam" - so the
# sample shows up as the FASTQ_ID in both the HTML report and the parquet.
echo_stderr "Generating MultiQC HTML report"
mkdir -p multiqc_html
uv run multiqc \
  --quiet \
  --outdir multiqc_html \
  "${PICARD_OUTPUT_DIR}/"

# Upload the MultiQC HTML report to S3
echo_stderr "Uploading MultiQC HTML report to S3"
aws s3 cp \
  --quiet \
  --content-type 'text/html' \
  "multiqc_html/multiqc_report.html" \
  "${OUTPUT_MULTIQC_HTML_URI}"

echo_stderr "Generating MultiQC parquet report"
mkdir -p multiqc_parquet
uv run multiqc \
  --quiet \
  --outdir multiqc_parquet \
  "${PICARD_OUTPUT_DIR}/"

# Upload the MultiQC parquet file to S3
echo_stderr "Uploading MultiQC parquet report to S3"
aws s3 cp \
  --quiet \
  "multiqc_parquet/multiqc_data/multiqc.parquet" \
  "${OUTPUT_MULTIQC_PARQUET_URI}"

# Convert the Picard metrics text to parquet.
# We write it to a local file (rather than streaming straight to S3) so that we
# can both upload it and derive the median insert size from the same parquet.
echo_stderr "Converting Picard metrics to parquet"
uv run python3 ./metrics_to_parquet.py < "${PICARD_METRICS_TXT}" \
  > "${PICARD_METRICS_PARQUET}"

# Upload the Picard metrics parquet to S3
echo_stderr "Uploading Picard metrics parquet to S3"
aws s3 cp \
  --quiet \
  "${PICARD_METRICS_PARQUET}" \
  "${OUTPUT_PICARD_PARQUET_URI}"

# Upload the Picard insert-size histogram PDF to S3
echo_stderr "Uploading Picard histogram PDF to S3"
aws s3 cp \
  --quiet \
  --content-type 'application/pdf' \
  "${PICARD_HISTOGRAM_PDF}" \
  "${OUTPUT_PICARD_PDF_URI}"

# Derive the insertSizeEstimate (MEDIAN_INSERT_SIZE) directly from the parquet
# we just produced, reusing the single parsing path in metrics_to_parquet.py,
# and upload the summary JSON to S3.
echo_stderr "Extracting median insert size from the Picard parquet and writing to S3"
uv run python3 ./get_median_insert_size.py "${PICARD_METRICS_PARQUET}" | \
aws s3 cp \
  --quiet \
  --content-type 'application/json' \
  - \
  "${OUTPUT_INSERT_SIZE_ESTIMATE_URI}"

echo_stderr "Picard insert size metrics collection complete"
