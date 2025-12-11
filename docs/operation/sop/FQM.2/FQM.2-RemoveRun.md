# FQM.1 - Remove Run

## Introduction

There may be times where an entire samplesheet is invalid / needs to be reprocessed.

## Procedure

The required operations are to be performed via the service's [API](../../../../README.md#api-endpoints).

Steps to follow:

### Collect all fastqs for a given instrument run id (fqr)

```shell
# Globals
INSTRUMENT_RUN_ID="20251124_LH00944_0002_B23CFMMLT4"

# Run fastq list
fastq_list="$( \
  curl --fail --silent --show-error --location \
    --request "GET" \
    --header "Accept: application/json" \
    --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
    --url "https://fastq.prod.umccr.org/api/v1/fastq?instrumentRunId=${INSTRUMENT_RUN_ID}" | \
  jq --raw-output \
    '
      .results
    ' \
)"
```

### Unlink the fastqs from the fastq sets (fqs)

This action will remove the FASTQ from the set (a pre-requisite before deleting the FASTQ itself).

```shell
# Iterate over each fastq to unlink and delete
for fastq_obj in $(jq -rc '.[]' <<< ${fastq_list}); do
  # Get loop vars
  fastq_id="$(jq -r '.id' <<< ${fastq_obj})"
  fastq_set_id="$(jq -r '.fastqSetId' <<< ${fastq_obj})"

  echo "Processing fastq ${fastq_id} from set ${fastq_set_id}"

  #
  # Unlink the fastq from the fastq set
  #
  echo " - Unlinking from set..."
  curl --fail --silent --show-error --location \
    --request "PATCH" \
    --header "Accept: application/json" \
    --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
    --url "https://fastq.prod.umccr.org/api/v1/fastqSet/${fastq_set_id}/unlinkFastq/${fastq_id}"

done
```

### Delete the fastqs

```shell
# Iterate over each fastq to unlink and delete
for fastq_obj in $(jq -rc '.[]' <<< ${fastq_list}); do
  fastq_id="$(jq -r '.id' <<< ${fastq_obj})"
  #
  # Delete the fastq
  #
  echo " - Deleting fastq..."
  curl --fail --silent --show-error --location \
    --request "DELETE" \
    --header "Accept: application/json" \
    --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
    --url "https://fastq.prod.umccr.org/api/v1/fastq/${fastq_id}"
done
```
