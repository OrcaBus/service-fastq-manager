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
  for file_iter in $(jq --raw-output 'split(",")[]' <<< "${files_list_str}"); do
	files_list_array+=("${file_iter}")
  done

  # Generate presigned urls from the file list
  for file_iter in "${files_list_array[@]}"; do
	presigned_array+=("$(aws s3 presign "${file_iter}")")
  done

  # Download the files and write to stdout
  wget --quiet \
	--output-document "${output_fifo}" \
  	"${presigned_array[@]}"
}

# Standard variables

# Check binaries
BINARIES_LIST=( \
  "curl" \
  "jq" \
  "minimap2" \
  "samtools" \
  "bedtools" \
  "aws" \
  "vcf2bed" \
  "uv" \
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
SITES_VCF_PATH="$(basename "${SITES_VCF_URI}")"

if [[ -z "${REFERENCE_FASTA_URI}" ]]; then
	echo_stderr "Could not find REFERENCE_FASTA_URI env var, exiting"
	exit 1
fi
REFERENCE_FASTA_PATH="$(basename "${REFERENCE_FASTA_URI}")"

if [[ -z "${OUTPUT_BAM_S3_URI}" ]]; then
	echo_stderr "Could not find OUTPUT_BAM_S3_URI env var, exiting"
	exit 1
fi

if [[ -z "${OUTPUT_FINGERPRINT_S3_URI}" ]]; then
	echo_stderr "Could not find OUTPUT_FINGERPRINT_S3_URI env var, exiting"
	exit 1
fi

if [[ -z "${SAMPLE_PREFIX}" ]]; then
	echo_stderr "Could not find SAMPLE_PREFIX env var, exiting"
	exit 1
fi


# Get the sites vcf uri
echo_stderr "Download the sites vcf file"
aws s3 cp "${SITES_VCF_URI}" "${SITES_VCF_PATH}"

# Download reference fasta
echo_stderr "Download the reference fasta file"
aws s3 cp "${REFERENCE_FASTA_URI}" "${REFERENCE_FASTA_PATH}"
aws s3 cp "${REFERENCE_FASTA_URI}.fai" "${REFERENCE_FASTA_PATH}.fai"

# Convert vcf file to a bed file
echo_stderr "Write bed file from sites vcf"
zcat "${SITES_VCF_PATH}" | vcf2bed > "${SITES_VCF_PATH%.vcf.gz}.bed"

# Slop the bed file
echo_stderr "Slop the bed file"
bedtools slop \
  -b 500 \
  -g "${REFERENCE_FASTA_PATH}.fai" \
  -i "${SITES_VCF_PATH%.vcf.gz}.bed" > "${SITES_VCF_PATH%.vcf.gz}.slop500.bed"

# Get the fasta reference from the bed file
echo_stderr "Generate a mini reference fasta from the slopped bed file"
bedtools getfasta \
  -fi "${REFERENCE_FASTA_PATH}" \
  -fo "${SITES_VCF_PATH%.vcf.gz}.slop500.fasta" \
  -bed "${SITES_VCF_URI%.vcf.gz}.slop500.bed"

# Now run the alignment
echo_stderr "Stream and align the fastq files to generate a bam file"
mkfifo "read_1_file_fifo"
mkfifo "read_2_file_fifo"

# Stream download the fastq files into minimap2
download_files "${READ_1_FILE_URI_LIST}" "read_1_file_fifo" & \
download_files "${READ_2_FILE_URI_LIST}" "read_2_file_fifo" & \
(
  minimap2 \
	-ax sr \
	-t 7 \
	"${SITES_VCF_URI%.vcf.gz}.slop500.fasta" \
	<(wget -q -O- "$(aws s3 presign "${READ_1_FILE_URI}")") \
	<(wget -q -O- "$(aws s3 presign "${READ_2_FILE_URI}")") | \
  samtools view \
	-F 4 \
	-t "${REFERENCE_FASTA_URI}" | \
  samtools sort \
	--output-fmt BAM \
	--write-index \
	-o sorted.bam \
	-
) & \
wait

# Delete fifos
rm read_1_file_fifo
rm read_2_file_fifo

# Now we have a bam, but the chromosomes are named as per the mini reference
# We need to rename them to match the full reference
# Use pysam to clean up the bam file
uv run python3 edit-bam.py "sorted.bam"

# Run somalier on the edited bam
somalier extract \
  --sites "${SITES_VCF_PATH}" \
  --fasta "${REFERENCE_FASTA_PATH}" \
  --out-dir "." \
  --sample-prefix "${SAMPLE_PREFIX}" \
  sorted.bam

# Upload bam
echo_stderr "Upload the bam and bai files to S3"
aws s3 cp sorted.bam "${OUTPUT_BAM_S3_URI}"
aws s3 cp sorted.bam.bai "${OUTPUT_BAM_S3_URI}.bai"

# Upload somalier fingerprint
aws s3 cp "${SAMPLE_PREFIX}.somalier" "${OUTPUT_FINGERPRINT_S3_URI}"
