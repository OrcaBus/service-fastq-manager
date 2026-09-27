#!/usr/bin/env bash

# Set to fail
set -euo pipefail

: '
Derive insertSizeEstimate from Picard CollectInsertSizeMetrics.

Sequali cannot observe an insert size larger than the read-pair length, so the
value it reports is capped. Instead we align a fixed sample of reads
(MAX_PICARD_READS, currently 10,000,000 read pairs) to the full hg38 reference
(no masking) and run Picard CollectInsertSizeMetrics to obtain a
MEDIAN_INSERT_SIZE that is not bounded by read length.

Flow:
1. Download the reference fasta (+ .fai index).
2. Download R1 (and R2 if set); for gzip inputs, decompress directly and
   truncate to MAX_PICARD_READS reads (the gzip-path read-cap guarantee).
3. Align with `minimap2 -ax sr` to the full hg38 reference (no masking) with a
   read group.
4. Filter with `samtools view -f 0x2 -F 0x900` (properly paired, exclude
   secondary + supplementary) plus optional --min-MQ; coordinate sort + index.
5. Run Picard CollectInsertSizeMetrics -> text metrics + histogram PDF.
6. Run MultiQC over the Picard output dir -> HTML report + parquet.
7. Convert the Picard metrics text to parquet via metrics_to_parquet.py.
8. Read MEDIAN_INSERT_SIZE from that parquet and write
   { "insertSizeEstimate": <value>, "insertSizeStdEstimate": <value>,
     "picardMetricsAvailable": true } JSON.
9. Upload PDF / picard parquet / MultiQC HTML / MultiQC parquet / summary JSON.

Special case - no properly-paired reads:
If the filtered BAM contains no properly-paired reads (e.g. an empty gzip input
or reads that never align as proper pairs), Picard has nothing to measure. We
detect this via an explicit read count, skip Picard / MultiQC / the PDF + parquet
uploads, and publish ONLY the summary JSON with null estimates and
"picardMetricsAvailable": false, then exit 0. Any OTHER Picard failure (with
properly-paired reads present) is still surfaced as a hard error.
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

# Inspect a captured PIPESTATUS array and fail loudly, naming the command that
# died and its exit code, so a mid-pipe failure is not swallowed into an opaque
# downstream error (e.g. minimap2 being OOM-killed surfaced only as
# "samtools view: error reading file -"). Call as:
#   some | pipe | line
#   PIPE_STATUS=("${PIPESTATUS[@]}")
#   check_pipestatus "stage-label" cmd0 cmd1 cmd2 ...
# where PIPE_STATUS must be captured on the line immediately after the pipeline
# (any intervening command overwrites PIPESTATUS). An exit code of 137 typically
# means the process was OOM-killed (128 + SIGKILL/9); 141 means SIGPIPE (128 + 13).
#
# Optionally, set the PIPE_TOLERATED_CODES array before calling to whitelist
# specific non-zero exit codes that should NOT be treated as failures. This is
# needed for `producer | head` pipes: once head has read its N lines it closes
# the pipe, so the producer is expected to die with SIGPIPE (141), which is
# benign here. PIPE_TOLERATED_CODES is consulted for every stage and reset to
# empty at the end of the call so it cannot leak into a later check.
check_pipestatus(){
  local stage_label="${1}"
  shift
  local -a cmd_names=( "$@" )
  local -a tolerated=( "${PIPE_TOLERATED_CODES[@]:-}" )
  local idx code tolerated_code is_tolerated
  for idx in "${!PIPE_STATUS[@]}"; do
    code="${PIPE_STATUS[${idx}]}"
    if [[ "${code}" -eq 0 ]]; then
      continue
    fi
    is_tolerated="false"
    for tolerated_code in "${tolerated[@]}"; do
      if [[ -n "${tolerated_code}" && "${code}" -eq "${tolerated_code}" ]]; then
        is_tolerated="true"
        break
      fi
    done
    if [[ "${is_tolerated}" == "true" ]]; then
      continue
    fi
    local cmd_name="${cmd_names[${idx}]:-cmd${idx}}"
    echo_stderr "Error! During '${stage_label}', command '${cmd_name}' (pipe position ${idx}) exited with status ${code}."
    if [[ "${code}" -eq 137 ]]; then
      echo_stderr "Exit code 137 usually means the process was OOM-killed. Consider raising the task memory."
    fi
    PIPE_TOLERATED_CODES=()
    exit "${code}"
  done
  PIPE_TOLERATED_CODES=()
}

# Standard parameters
MINIMAP_THREADS="8"
SAMTOOLS_THREADS="8"

# minimap2 max fragment length (-F).
# The `-ax sr` short-read preset hardcodes max_frag_len = 800, which is the
# maximum insert size at which minimap2 will flag a read pair as properly paired
# (SAM flag 0x2). Because we downstream filter to properly-paired reads only
# (`samtools view --require-flags 0x2`), any pair with a true insert > 800 bp is
# dropped before Picard sees it, so the insert-size histogram falls off a cliff
# at exactly 800 bp. Long-fragment libraries (e.g. TsqNano WGS) genuinely extend
# well beyond 800 bp, so we raise the cap here to capture the full distribution.
# See minimap2 options.c (`sr` preset) and `-F NUM` in the minimap2 manual.
MINIMAP_MAX_FRAG_LEN="5000"

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
#
# `head` closes the pipe as soon as it has its TRUNCATE_LINES, so pigz is
# expected to receive SIGPIPE and exit 141 (128 + 13). That is the normal, benign
# outcome here (the input almost always has more reads than the cap), so we
# tolerate pigz exit 141 via PIPE_TOLERATED_CODES while check_pipestatus still
# surfaces any genuine pigz failure (e.g. a corrupt gzip -> exit 1) and any head
# failure.
echo_stderr "Truncating R1 to the first ${MAX_PICARD_READS} reads"
pigz --decompress --stdout "${R1_GZIP_PATH}" | \
head -n "${TRUNCATE_LINES}" \
  > "${R1_TRUNCATED_PATH}"
PIPE_STATUS=("${PIPESTATUS[@]}")
PIPE_TOLERATED_CODES=( 141 )
check_pipestatus "R1 decompress+truncate" "pigz" "head"

# Download R2 if provided and truncate the same way
HAS_R2="false"
if [[ -v R2_INPUT_URI ]]; then
  HAS_R2="true"
  echo_stderr "Starting download of '${R2_INPUT_URI}'"
  download_gz_file \
    "${R2_INPUT_URI}" \
    "${R2_GZIP_PATH}"
  echo_stderr "Finished download of '${R2_INPUT_URI}'"

  # See the R1 truncation note above: pigz exit 141 (SIGPIPE from head closing
  # the pipe early) is the expected benign outcome and is tolerated; any other
  # pigz failure or a head failure is surfaced.
  echo_stderr "Truncating R2 to the first ${MAX_PICARD_READS} reads"
  pigz --decompress --stdout "${R2_GZIP_PATH}" | \
  head -n "${TRUNCATE_LINES}" \
    > "${R2_TRUNCATED_PATH}"
  PIPE_STATUS=("${PIPESTATUS[@]}")
  PIPE_TOLERATED_CODES=( 141 )
  check_pipestatus "R2 decompress+truncate" "pigz" "head"
fi

# Align with minimap2 to the FULL hg38 reference (no masking), attach a read
# group keyed on the fastq id (fall back to the library id), filter to
# properly-paired reads while excluding secondary (0x100) + supplementary (0x800)
# = 0x900 alignments, optionally apply a MAPQ threshold, then coordinate sort +
# index. The per-tool flags are assembled into the MINIMAP2_ARGS and
# SAMTOOLS_VIEW_ARGS arrays below.
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

# Build the minimap2 args as an array (mirrors SAMTOOLS_VIEW_ARGS above).
#   -ax sr                  short-read alignment preset, output SAM
#   -F MINIMAP_MAX_FRAG_LEN override the sr preset's 800 bp max fragment length
#                           (see MINIMAP_MAX_FRAG_LEN above) so long-fragment
#                           libraries are not truncated by the proper-pair filter
#   -v1                     warnings only (quiet)
#   -t MINIMAP_THREADS      alignment threads
#   -R @RG...               read group keyed on the fastq id (fallback library id)
# The reference and read inputs are passed as positional args at the call site.
MINIMAP2_ARGS=( \
  "-ax" "sr" \
  "-F" "${MINIMAP_MAX_FRAG_LEN}" \
  "-v1" \
  "-t" "${MINIMAP_THREADS}" \
  "-R" "@RG\tID:${RG_SAMPLE}\tSM:${RG_SAMPLE}" \
)

# Note on failure reporting: this is a three-stage pipe. Under `set -o pipefail`
# a failure in any stage fails the line, but the shell's own $? only reflects the
# last stage, so a minimap2 OOM kill would otherwise surface only as the
# downstream "samtools view: error reading file -". We capture PIPESTATUS on the
# line immediately after the pipeline (it is clobbered by any later command) and
# hand it to check_pipestatus, which names the actual failing stage and its exit
# code (137 => OOM-killed).
echo_stderr "Aligning reads to the full reference genome with minimap2"
minimap2 \
  "${MINIMAP2_ARGS[@]}" \
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
PIPE_STATUS=("${PIPESTATUS[@]}")
check_pipestatus "minimap2 alignment" "minimap2" "samtools view" "samtools sort"

# Run Picard CollectInsertSizeMetrics to produce the text metrics file and the
# insert-size histogram PDF.
#
# --MINIMUM_PCT 0: by default Picard discards any read-orientation category
# holding < 5% of the aligned pairs. On a small fixed sample this
# can discard every category, producing no metrics file at all ("All data
# categories were discarded because they contained < 0.05 ..."). Setting it to 0
# keeps all pairs so the metrics are always emitted.
#
# Note: the "Unable to load libgkl_compression.so ... can't load AMD 64 .so on a
# AARCH64 platform" line is a benign WARN - it is Intel's x86-only GKL native
# acceleration library. Picard is a JVM tool and runs fine on arm64, falling back
# to pure-Java (de)compression.
mkdir -p "${PICARD_OUTPUT_DIR}"

# Build the Picard CollectInsertSizeMetrics args as an array (mirrors
# MINIMAP2_ARGS / SAMTOOLS_VIEW_ARGS above).
PICARD_COLLECT_INSERT_SIZE_METRICS_ARGS=( \
  "--INPUT" "${SORTED_FILTERED_BAM}" \
  "--OUTPUT" "${PICARD_METRICS_TXT}" \
  "--Histogram_FILE" "${PICARD_HISTOGRAM_PDF}" \
  "--REFERENCE_SEQUENCE" "${REF_GENOME_PATH}" \
  "--MINIMUM_PCT" "0" \
)

# Before running Picard, count how many properly-paired primary reads survived
# the alignment + filtering above. Picard CollectInsertSizeMetrics derives the
# insert-size distribution exclusively from properly-paired reads, so a BAM with
# none of them (an empty / near-empty gzip input, or reads that simply do not
# align as proper pairs) can never yield a metrics file. That is the one benign,
# expected outcome we treat as "no insert size available" rather than a failure.
#
# We make that decision here off an explicit read count rather than inferring it
# from Picard's silence, so that a genuine Picard error (which we run separately
# below) is never misread as "too few reads".
#
# The SAMTOOLS_VIEW_ARGS already restrict to properly-paired (0x2) primary
# alignments (excluding 0x900), so re-applying them to `samtools view -c` counts
# exactly the reads Picard would consume.
echo_stderr "Counting properly-paired reads in the filtered BAM"
PROPERLY_PAIRED_READ_COUNT="$( \
  samtools view \
    -c \
    "${SAMTOOLS_VIEW_ARGS[@]}" \
    "${SORTED_FILTERED_BAM}" \
)"
echo_stderr "Found ${PROPERLY_PAIRED_READ_COUNT} properly-paired reads in the filtered BAM"

if [[ "${PROPERLY_PAIRED_READ_COUNT}" -eq 0 ]]; then
  # Clean "too few reads aligned as proper pairs" exit.
  #
  # There is nothing for Picard to measure, so we skip Picard, MultiQC, the PDF
  # and both parquet uploads entirely (those objects would never exist) and
  # publish ONLY the summary JSON with null estimates plus a
  # picardMetricsAvailable=false flag. The step function reads this flag to skip
  # the picard file sync-check and to omit the picard report block when updating
  # the fastq object, and writes null insertSizeEstimate / insertSizeStdEstimate
  # into the top level QC metrics.
  echo_stderr "No properly-paired reads found; skipping Picard and emitting null insert size estimates."

  INSERT_SIZE_ESTIMATE_JSON="/tmp/${FASTQ_ID}.insert_size_estimate.json"
  cat > "${INSERT_SIZE_ESTIMATE_JSON}" <<'EOF'
{
  "insertSizeEstimate": null,
  "insertSizeStdEstimate": null,
  "picardMetricsAvailable": false
}
EOF

  echo_stderr "Writing null insert size estimate to S3"
  aws s3 cp \
    --content-type 'application/json' \
    "${INSERT_SIZE_ESTIMATE_JSON}" \
    "${OUTPUT_INSERT_SIZE_ESTIMATE_URI}"

  echo_stderr "Picard insert size metrics collection complete (no properly-paired reads)"
  exit 0
fi

echo_stderr "Running Picard CollectInsertSizeMetrics"
picard CollectInsertSizeMetrics \
  "${PICARD_COLLECT_INSERT_SIZE_METRICS_ARGS[@]}"

# At this point we know the BAM contained properly-paired reads, so a missing
# metrics file is NOT the benign "too few reads" case handled above - it is a
# genuine Picard failure and must be surfaced (exit 1) for investigation rather
# than silently downgraded to null.
if [[ ! -s "${PICARD_METRICS_TXT}" ]]; then
  echo_stderr "Error! Picard did not produce a metrics file at '${PICARD_METRICS_TXT}'"
  echo_stderr "despite ${PROPERLY_PAIRED_READ_COUNT} properly-paired reads being present."
  echo_stderr "This is an unexpected Picard failure and requires investigation."
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
#
# We deliberately do NOT pipe the python stdout straight into `aws s3 cp -`.
# get_median_insert_size.py reads the parquet via pandas/pyarrow, and the Arrow
# C++ runtime tears down its resources at interpreter shutdown. When aws closes
# its stdin the instant it has buffered the tiny JSON payload, the python
# process' final stdout flush can race with that teardown and the C++ runtime
# aborts with "terminate called without an active exception" (SIGABRT, exit
# 134). Under `set -euo pipefail` that intermittently killed the whole task
# right at this final step, with no error surfaced (aws ran with --quiet).
#
# Writing to a local file first removes the pipe (and therefore the race)
# entirely, and lets us upload from a normal file with the error output intact.
INSERT_SIZE_ESTIMATE_JSON="/tmp/${FASTQ_ID}.insert_size_estimate.json"
echo_stderr "Extracting median insert size from the Picard parquet"
uv run python3 ./get_median_insert_size.py "${PICARD_METRICS_PARQUET}" \
  > "${INSERT_SIZE_ESTIMATE_JSON}"

echo_stderr "Writing insert size estimate to S3"
aws s3 cp \
  --content-type 'application/json' \
  "${INSERT_SIZE_ESTIMATE_JSON}" \
  "${OUTPUT_INSERT_SIZE_ESTIMATE_URI}"

echo_stderr "Picard insert size metrics collection complete"
