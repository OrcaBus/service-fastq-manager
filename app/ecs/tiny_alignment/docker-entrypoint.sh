#!/usr/bin/env bash

set -euo pipefail

: '
Performs the following tasks

Given a list of gzip compressed fastq files,

Set up
1. Download reference fasta
2. Download sites vcf
3. Create bedtools slop around sites file
4. Generate reference fasta from bedtools slop
5. Generate minimap2 index from mini reference fasta

Run
1. Stream the input files into minimap2, we may use orad for this if the file ends with ".ora"
2. Write the bam file to disk, omitting unmapped reads
3. Sort and index the bam file
4. Upload the bam and bai files to S3 to the fingerprinting bucket
'

# Quick functions
echo_stderr(){
  echo "$(date -Iseconds):" "${@}" 1>&2
}

download_files(){
  local files_list_str="$1"
  local output_fifo="$2"
  local files_list_array=()
  local presigned_array=()

  # Convert the file list string to an array
  for file_iter in $( \
  	jq \
  	  --null-input \
  	  --raw-output \
  	  --arg filesList "${files_list_str}" \
  	  '
  	    $filesList | split(",")[]
  	  ' \
  ); do
	files_list_array+=("${file_iter}")
  done

  # Generate presigned urls from the file list
  for file_iter in "${files_list_array[@]}"; do
    #
		presigned_array+=("$(aws s3 presign "${file_iter}")")
  done

  # Download the files and write to stdout
  wget --quiet \
	--output-document "${output_fifo}" \
  	"${presigned_array[@]}"
}

# Standard variables
MINIMAP_THREADS="8"
SAMTOOLS_THREADS="8"
MAX_AVG_READ_SIZE="150"

# Check binaries
BINARIES_LIST=( \
  "curl" \
  "jq" \
  "minimap2" \
  "samtools" \
  "bedtools" \
  "aws" \
  "convert2bed" \
  "python3" \
  "somalier" \
)

for binary_iter in "${BINARIES_LIST[@]}"; do
	if ! command -v "${binary_iter}" &> /dev/null; then
		echo_stderr "Could not find ${binary_iter} binary, exiting"
		exit 1
	fi
done

# Check env vars
if [[ -z "${SITES_VCF_URI}" ]]; then
	echo_stderr "Could not find SITES_VCF_URI env var, exiting"
	exit 1
fi

# Set SITES VCF Vars
SITES_VCF_PATH="$(basename "${SITES_VCF_URI}")"
SITES_BED_PATH="${SITES_VCF_PATH%.vcf.gz}.bed"
SITES_BED_SLOP_150_PATH="${SITES_VCF_PATH%.vcf.gz}.slop150.bed"
SITES_BED_SLOP_1_PATH="${SITES_VCF_PATH%.vcf.gz}.slop1.bed"
SITES_FASTA_SLOP_150_PATH="${SITES_VCF_PATH%.vcf.gz}.slop150.fasta"

if [[ -z "${REF_GENOME_URI}" ]]; then
	echo_stderr "Could not find REF_GENOME_URI env var, exiting"
	exit 1
fi

# Set REF GENOME Vars
REF_GENOME_PATH="$(basename "${REF_GENOME_URI}")"
SITES_FASTA_SLOP_150_MASKED_PATH="${SITES_VCF_PATH%.vcf.gz}.slop150.masked.bed"
REF_GENOME_MASKED_PATH="${REF_GENOME_PATH%.fasta}.masked.fasta"

if [[ -z "${OUTPUT_FILTERED_BAM_URI}" ]]; then
	echo_stderr "Could not find OUTPUT_FILTERED_BAM_URI env var, exiting"
	exit 1
fi

if [[ -z "${OUTPUT_FINGERPRINT_S3_URI}" ]]; then
	echo_stderr "Could not find OUTPUT_FINGERPRINT_S3_URI env var, exiting"
	exit 1
fi

if [[ -z "${SAMPLE_NAME}" ]]; then
	echo_stderr "Could not find SAMPLE_NAME env var, exiting"
	exit 1
fi

# Get the sites vcf uri
echo_stderr "Download the sites vcf file"
aws s3 cp --quiet "${SITES_VCF_URI}" "${SITES_VCF_PATH}"

# Download reference fasta
echo_stderr "Download the reference fasta file"
aws s3 cp --quiet "${REF_GENOME_URI}" "${REF_GENOME_PATH}"
aws s3 cp --quiet "${REF_GENOME_URI}.fai" "${REF_GENOME_PATH}.fai"

# Run bedtools against the input vcf file to slop the regions by 1 bp either side
# Create a bedfile from a vcf
zcat "${SITES_VCF_PATH}" | \
convert2bed \
  --input=vcf \
  --do-not-sort \
> "${SITES_BED_PATH}"

# Slop the bed file
echo_stderr "Slop the bed file"
bedtools slop \
  -b "${MAX_AVG_READ_SIZE}" \
  -g "${REF_GENOME_PATH}.fai" \
  -i "${SITES_BED_PATH}" > "${SITES_BED_SLOP_150_PATH}"
# Repeat for filtering the final alignment bam
bedtools slop \
 -b 1 \
 -g "${REF_GENOME_PATH}.fai" \
 -i "${SITES_BED_PATH}" > "${SITES_BED_SLOP_1_PATH}"

# Get the fasta reference from the bed file
echo_stderr "Generate a mini reference fasta from the slopped bed file"
bedtools getfasta \
  -fi "${REF_GENOME_PATH}" \
  -fo "${SITES_FASTA_SLOP_150_PATH}" \
  -bed "${SITES_BED_SLOP_150_PATH}"

# Make a masked version of the full reference
bedtools complement \
  -i "${SITES_BED_SLOP_150_PATH}" \
  -g "${REF_GENOME_PATH}.fai" > "${SITES_FASTA_SLOP_150_MASKED_PATH}"
bedtools maskfasta \
  -fi "${REF_GENOME_PATH}" \
  -fo "${REF_GENOME_MASKED_PATH}" \
  -bed "${SITES_FASTA_SLOP_150_MASKED_PATH}"

# Index the mini reference fasta with samtools
echo_stderr "Index the slopped 150 path"
samtools faidx "${SITES_FASTA_SLOP_150_PATH}"

# Index the masked reference genome
echo_stderr "Index the masked reference genome"
samtools faidx "${REF_GENOME_MASKED_PATH}"

# Set FASTQ VARs
READ_1_FILE_FIFO="read_1_file_fifo"
READ_2_FILE_FIFO="read_2_file_fifo"
READ_1_GZIP_FILE="combined.filtered.R1.fastq.gz"
READ_2_GZIP_FILE="combined.filtered.R2.fastq.gz"

# Now run the alignment
echo_stderr "Stream and align the fastq files to generate two filtered fastq files"
mkfifo \
  "${READ_1_FILE_FIFO}" "${READ_2_FILE_FIFO}"

# Stream the fastq files into minimap2 with
# the mini reference fasta, -ax for short reads, -t 4 to use four threads
# SAM file is then piped into 'samtools view' to remove unmapped reads (0x4) where the mate is also unmapped (0x8) = 12
# Before then being sorted, compressed and indexed with 'samtools sort'
# Now we have a bam, but the chromosomes are named as per the mini reference
# So easiest to just convert back to fastq and realign to the full reference
# Since we have removed unmapped reads already, this should be quick

# Set View Vars
EXCLUDE_FLAGS="12"

# Start the piping game!
download_files "${READ_1_FILE_URI_LIST}" "${READ_1_FILE_FIFO}" & \
download_files "${READ_2_FILE_URI_LIST}" "${READ_2_FILE_FIFO}" & \
(
  minimap2 \
	-ax sr \
	-v1 \
	-t "${MINIMAP_THREADS}" \
	"${SITES_FASTA_SLOP_150_PATH}" \
	"${READ_1_FILE_FIFO}" \
	"${READ_2_FILE_FIFO}" | \
  samtools view \
    --uncompressed \
    --exclude-flags "${EXCLUDE_FLAGS}" | \
  samtools sort \
    -u \
    -n \
    --threads "${SAMTOOLS_THREADS}" \
  	- | \
  samtools fastq \
    -1 "${READ_1_GZIP_FILE}" \
    -2 "${READ_2_GZIP_FILE}" \
    -0 /dev/null \
    -s /dev/null
) & \
wait

# Delete fifos
rm "${READ_1_FILE_FIFO}"
rm "${READ_2_FILE_FIFO}"

# Run the alignment on the masked reference genome
# Set Realignment step vars
OUTPUT_FILTERED_BAM="sorted.filtered.bam"
MIN_MAPPING_QUALITY="60"
echo_stderr "Re-align the remaining fastq files back to the full reference (masked)"
minimap2 \
  -ax sr \
  -v1 \
  -t "${MINIMAP_THREADS}" \
  -R "@RG\tID:${SAMPLE_NAME}\tSM:${SAMPLE_NAME}" \
  "${REF_GENOME_MASKED_PATH}" \
  "${READ_1_GZIP_FILE}" \
  "${READ_2_GZIP_FILE}" | \
samtools view \
  --uncompressed \
  --min-MQ "${MIN_MAPPING_QUALITY}" \
  -t "${REF_GENOME_PATH}.fai" \
  --target-file "${SITES_BED_SLOP_1_PATH}" \
  - | \
samtools sort \
  --output-fmt BAM \
  -o "${OUTPUT_FILTERED_BAM}##idx##${OUTPUT_FILTERED_BAM}.bai" \
  --write-index \
  -

# Run somalier on the edited tiny bam
# Set SOMALIER Vars
EXTRACTED_DIR="extracted"

echo_stderr "Run somalier to generate the fingerprint"
mkdir -p "${EXTRACTED_DIR}"
SOMALIER_SAMPLE_NAME="${SAMPLE_NAME}" \
somalier extract \
  --sites "${SITES_VCF_PATH}" \
  --fasta "${REF_GENOME_PATH}" \
  --out-dir "${EXTRACTED_DIR}" \
  "${OUTPUT_FILTERED_BAM}"

# Upload bam
echo_stderr "Upload the bam and bai files to S3"
aws s3 cp --quiet "${OUTPUT_FILTERED_BAM}" "${OUTPUT_FILTERED_BAM_URI}"
aws s3 cp --quiet "${OUTPUT_FILTERED_BAM}".bai "${OUTPUT_FILTERED_BAM_URI}.bai"

# Upload somalier fingerprint
echo_stderr "Upload the somalier fingerprint to S3"
aws s3 cp --quiet "${EXTRACTED_DIR}/${SAMPLE_NAME}.somalier" "${OUTPUT_FINGERPRINT_S3_URI}"
