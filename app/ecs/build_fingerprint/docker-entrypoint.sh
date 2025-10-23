#!/usr/bin/env bash

: '
Perform the following tasks

0. Check for required tools
- aws
- curl
- wget
- samtools
- bedtools
- jq

1. Check inputs, ensure all environment variables are set as expected

// SET
ORCABUS_TOKEN_SECRET_ID
HOSTNAME_SSM_PARAMETER_NAME

// SOMEWHAT DYNAMIC
REF_GENOME_URI
SITES_VCF_URI

// DYNAMIC
INPUT_BAM_URI
SAMPLE_PREFIX
OUTPUT_FILTERED_BAM_URI
OUTPUT_FINGERPRINT_URI

2. Download reference genome, sites file and bam index

3. Run bedtools against the input vcf file to slop the regions by 10 bp either side

4. With our new bed file, we can use samtools view to extract the reads from the input bam file
However, we also export our AWS credentials to ensure we can read from the S3 bucket directly.
We then write the filtered and sorted small bam file with an index

5. Run somalier on the new bam file against the reference genome and the input vcf file

6. Upload our new fingerprint and our filtered bam to our fingerprints bucket.
We need to upload the filtered bam as the holmes service does not take fingerprints as inputs.
So instead we filter the bam to only the relevant sites and upload that alongside the fingerprint.
We can then send the filtered bam to holmes to reperform the fingerprinting process.
'

# Set to fail
set -euo pipefail

# Functions
echo_stderr(){
  echo "$(date -Iseconds)" "${@}" >&2
}

get_orcabus_token(){
  : '
  Use the ORCABUS_TOKEN_SECRET_ID to get a token from AWS Secrets Manager
  '
  aws secretsmanager get-secret-value \
  	--secret-id "${ORCABUS_TOKEN}" \
  	--query 'SecretString' \
  	--output json | \
  jq --raw-output \
    'fromjson | .id_token'
}

get_hostname(){
  : '
  Use the HOSTNAME_SSM_PARAMETER_NAME to get the hostname from AWS SSM Parameter Store
  '
  aws ssm get-parameter \
  	--name "${HOSTNAME_SSM_PARAMETER_NAME}" \
  	--query 'Parameter.Value' \
  	--output text
}

get_presigned_url_from_uri(){
  : '
  Use the filemanager to get the s3 object id given a uri
  '
  local uri="$1"
  local bucket
  local key

  # Extract bucket and key from the URI
  bucket="$(python3 -c "from urllib.parse import urlparse; print(urlparse('$uri').netloc)")"
  key="$(python3 -c "from urllib.parse import urlparse; print(urlparse('$uri').path.lstrip('/'))")"

  # Get s3 object id
  s3_object_id="$( \
	curl \
	  --request GET \
	  --fail --silent --location --show-error \
	  --header "Accept: application/json " \
	  --header "Authorization: Bearer $(get_orcabus_token)" \
	  --url "https://file.$(get_hostname)/api/v1/s3?bucket=${bucket}&key=${key}&currentState=true" | \
	jq --raw-output \
	  '
		if .results | length == 0 then
		  error("No results found for the given bucket and key")
		elif .results | length > 1 then
		  error("Multiple results found for the given bucket and key")
		else
		  .results[0].s3ObjectId
		end
	  ' \
  )"

  # Return the presigned URL
  curl \
    --request GET \
    --fail --silent --location --show-error \
    --header "Accept: application/json " \
    --header "Authorization: Bearer $(get_orcabus_token)" \
    --url "https://file.$(get_hostname)/api/v1/s3/presign/${s3_object_id}" | \
  jq --raw-output
}

download_uri(){
  : '
  Download a file from a given URI using wget
  '
  local uri="$1"
  local output_path="$2"

  # Create the output directory if it does not exist
  mkdir -p "$(dirname "${output_path}")"

  # Download the file
  wget \
    --quiet \
    --output-document "${output_path}" \
    "$(get_presigned_url_from_uri "${uri}")"
}


# Globals
REFERENCE_GENOME_PATH="reference.fasta"
SITES_VCF_PATH="sites.vcf.gz"
FULL_BAM_INDEX="input.bam.bai"
FILTERED_BAM_PATH="filtered.bam"
SITES_BED_PATH="sites.bed"


# 0. Check for required tools
echo_stderr "Part 0: Checking tools"
REQUIRED_TOOLS=( \
  "aws" \
  "curl" \
  "wget" \
  "samtools" \
  "jq" \
  "bedtools" \
  "somalier" \
  "python3" \
)
for tool in "${REQUIRED_TOOLS[@]}"; do
	if ! command -v "$tool" &> /dev/null; then
		echo "Error: $tool is not installed." >&2
		exit 1
	fi
done

# 1. Check inputs, ensure all environment variables are set as expected
echo_stderr "Part 1: Checking inputs"
REQUIRED_VARS=( \
  "ORCABUS_TOKEN_SECRET_ID" \
  "HOSTNAME_SSM_PARAMETER_NAME" \
  "REF_GENOME_URI" \
  "SITES_VCF_URI" \
  "INPUT_BAM_URI" \
  "OUTPUT_FILTERED_BAM_URI" \
  "OUTPUT_FINGERPRINT_URI" \
  "SAMPLE_PREFIX" \
)
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
	echo "Error: Environment variable $var is not set." >&2
	exit 1
  fi
done

# 2. Download reference genome, sites file and bam index
echo_stderr "Part 2: Downloading reference genome, sites file and bam index"

# Reference genome
aws s3 cp "${REF_GENOME_URI}" "${REFERENCE_GENOME_PATH}"
aws s3 cp "${REF_GENOME_URI}.fai" "${REFERENCE_GENOME_PATH}.fai"
aws s3 cp "${REF_GENOME_URI%.fa}" "${REFERENCE_GENOME_PATH%.fa}.dict"

# Sites vcf
aws s3 cp "${SITES_VCF_URI}" "${SITES_VCF_PATH}"
aws s3 cp "${SITES_VCF_URI}.tbi" "${SITES_VCF_PATH}.tbi"

# Input bam index
download_uri "${INPUT_BAM_URI}.bai" "${FULL_BAM_INDEX}"

# 3. Run bedtools against the input vcf file to slop the regions by 1 bp either side
echo_stderr "Part 3: Creating slopped bed file from vcf"
bedtools slop \
 -b 1 \
 -i "${SITES_VCF_PATH}" \
 -g "${REFERENCE_GENOME_PATH%.fa}.dict" > "${SITES_BED_PATH}"

# 4. Use samtools view to extract the reads from the input bam file
echo_stderr "Part 4: Extracting sites from input bam into filtered vcf"
samtools view \
  --bam \
  --customized-index \
  --target-file "${SITES_BED_PATH}" \
  "$( \
    get_presigned_url_from_uri \
      "${INPUT_BAM_URI}"
  )" \
  "${FULL_BAM_INDEX}" | \
samtools sort \
  -o "${FILTERED_BAM_PATH}" \
  --write-index

# 5. Run somalier on the new bam file against the reference genome and the input vcf file
echo_stderr "Part 5: Running somalier to create fingerprint"
mkdir -p extracted
somalier extract \
  --sites "${SITES_VCF_PATH}" \
  --fasta "${REFERENCE_GENOME_PATH}" \
  --out-dir "extracted" \
  --sample-prefix "${SAMPLE_PREFIX}" \
  "${FILTERED_BAM_PATH}"

# 6. Upload our new fingerprint and our filtered bam to our fingerprints bucket.
echo_stderr "Part 6: Uploading filtered bam and fingerprint"
aws s3 cp \
  "${FILTERED_BAM_PATH}" \
  "${OUTPUT_FILTERED_BAM_URI}"
aws s3 cp \
  "${FILTERED_BAM_PATH}.bai" \
  "${OUTPUT_FILTERED_BAM_URI}.bai"
aws s3 cp \
  "extracted/${SAMPLE_PREFIX}.somalier" \
  "${OUTPUT_FINGERPRINT_URI}"
