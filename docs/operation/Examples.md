# Usage Examples

All usage examples can be replicated via the [API](../../README.md#api-endpoints)

- [Setup: Authentication](#setup-authentication)
- [Get Fastqs (api/v1/fastq)](#get-fastqs-apiv1fastq)
- [Get Fastq by RGID (api/v1/rgid/)](#get-fastq-by-rgid-apiv1rgid)
- [Get Fastq Sets (api/v1/fastqSet)](#get-fastq-sets-apiv1fastqset)
- [Run Jobs on Fastqs](#run-jobs-on-fastqs)
- [Creating Fastq Objects](#creating-fastq-objects)
- [Deleting Fastq Objects](#deleting-fastq-objects)
- [Amending Fastqs](#amending-fastqs)
- [Amending Fastq Sets](#amending-fastq-sets)
- [For Download / Streaming](#for-download--streaming)
- [Comparing Fastqs within a fastq set](#comparing-fastqs-within-a-fastq-set)
- [Comparing Two Fastq Sets](#comparing-two-fastq-sets)
- [MultiQC Summaries](#multiqc-summaries)
  - [Get all fastqs](#get-all-fastqs)
  - [Get missing QC stats](#get-missing-qc-stats)
  - [Generate MultiQC Summary](#generate-multiqc-summary)

## Setup: Authentication

```bash
export AWS_PROFILE='umccr-production'  # Or your desired AWS profile
export ORCABUS_TOKEN="$( \
  aws secretsmanager get-secret-value \
  --secret-id orcabus/token-service-jwt \
  --output json \
  --query SecretString | \
  jq --raw-output \
    '
      fromjson |
      .id_token
    '
  ) \
)"
```

## Get Fastqs (api/v1/fastq)

A user can retrieve a list of fastqs by using at least one of the following:

- instrument run id (241024_A00130_0336_BHW7MVDSXC)
- lab metadata query parameter
  - Can be in either orcabus id format (i.e lib.01JBB5Y3901PA0X3FBMWBKYNMB) or readable format L2401538
  - library / sample / subject / individual / project
  - Specify [] after the query parameter to set multiple attributes for the same query parameter
- lane number or index, but must also specify the instrument run id if either of these are set.

A user may also add in the following boolean parameters to affect the response:

- includeS3Details
  - If set to true, the response will include the S3 URI and storage class of the fastq file.

By default, only 'valid' fastq files are returned. A fastq file may be considered invalid if the
sequencing run has been marked as 'failed' by the lab. Or the library failed and has been rerun in a later sequencing run.

<details>

<summary>Click to expand</summary>

```
curl \
  --fail --silent --show-error --location \
  --request "GET" \
  --header "Accept: application/json" \
  --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
  --url "https://fastq.prod.umccr.org/api/v1/fastq?instrumentRunId=241024_A00130_0336_BHW7MVDSXC&includeS3Details=true&library=L2401544" | \
jq --raw-output \
 '.results'
```

Gives

```json5
[
  {
    id: 'fqr.01JN26H64C5NTRGX399RXH4P2R',
    fastqSetId: 'fqs.01JN26H68NW44XY8TYHFJJHHDT',
    index: 'CAAGCTAG+CGCTATGT',
    lane: 3,
    instrumentRunId: '241024_A00130_0336_BHW7MVDSXC',
    library: {
      orcabusId: 'lib.01JBMW08H093THDFYS4467C2RW',
      libraryId: 'L2401544',
    },
    platform: 'Illumina',
    center: 'UMCCR',
    date: '2024-10-24T00:00:00',
    readSet: {
      r1: {
        ingestId: '01938dc7-1960-7a71-b035-696ad6befdd1',
        s3Uri: 's3://archive-prod-fastq-503977275616-ap-southeast-2/v1/year=2024/month=10/241024_A00130_0336_BHW7MVDSXC/20241122aaf5f88f/WGS_TsqNano/PTC_TSqN241021_L2401544_S7_L003_R1_001.fastq.ora',
        storageClass: 'DeepArchive',
        gzipCompressionSizeInBytes: 5159414821,
        rawMd5sum: 'c18b21229faa8dbce8d5fbe6a43b686e', // pragma: allowlist secret
      },
      r2: {
        ingestId: '01938dc7-3121-7ca0-a09d-27aa4091437d',
        s3Uri: 's3://archive-prod-fastq-503977275616-ap-southeast-2/v1/year=2024/month=10/241024_A00130_0336_BHW7MVDSXC/20241122aaf5f88f/WGS_TsqNano/PTC_TSqN241021_L2401544_S7_L003_R2_001.fastq.ora',
        storageClass: 'DeepArchive',
        gzipCompressionSizeInBytes: 5524315718,
        rawMd5sum: 'e5683457609a56d7f65dd2d95476d9a6', // pragma: allowlist secret
      },
      compressionFormat: null,
    },
    qc: null,
    ntsm: null,
    readCount: null,
    baseCountEst: null,
    isValid: true,
  },
  {
    id: 'fqr.01JN26H66MD5MA6402Y4JACDHV',
    fastqSetId: 'fqs.01JN26H68NW44XY8TYHFJJHHDT',
    index: 'CAAGCTAG+CGCTATGT',
    lane: 2,
    instrumentRunId: '241024_A00130_0336_BHW7MVDSXC',
    library: {
      orcabusId: 'lib.01JBMW08H093THDFYS4467C2RW',
      libraryId: 'L2401544',
    },
    platform: 'Illumina',
    center: 'UMCCR',
    date: '2024-10-24T00:00:00',
    readSet: {
      r1: {
        ingestId: '01938dc7-0ca6-7be3-9910-ec4e74ec210f',
        s3Uri: 's3://archive-prod-fastq-503977275616-ap-southeast-2/v1/year=2024/month=10/241024_A00130_0336_BHW7MVDSXC/20241122aaf5f88f/WGS_TsqNano/PTC_TSqN241021_L2401544_S7_L002_R1_001.fastq.ora',
        storageClass: 'DeepArchive',
        gzipCompressionSizeInBytes: 4763336257,
        rawMd5sum: '5bb40403dd880a0d749940e732120c47', // pragma: allowlist secret
      },
      r2: {
        ingestId: '01938dc7-15ff-77a2-b455-703202b7be68',
        s3Uri: 's3://archive-prod-fastq-503977275616-ap-southeast-2/v1/year=2024/month=10/241024_A00130_0336_BHW7MVDSXC/20241122aaf5f88f/WGS_TsqNano/PTC_TSqN241021_L2401544_S7_L002_R2_001.fastq.ora',
        storageClass: 'DeepArchive',
        gzipCompressionSizeInBytes: 5080028551,
        rawMd5sum: '29bbcab9d1c551a72e9b8cf2c855915d', // pragma: allowlist secret
      },
      compressionFormat: null,
    },
    qc: null,
    ntsm: null,
    readCount: null,
    baseCountEst: null,
    isValid: true,
  },
]
```

</details>

## Get Fastq by RGID (api/v1/rgid/<rgid>)

You may also grab results by the rgid.

The rgid is noted by `<index>.<lane>.<instrument_run_id>` for Illumina data.

Since this endpoint only returns one result, the result is not wrapped in any pagination.

<details>

<summary>Click to expand!</summary>

```
curl \
  --fail --silent --show-error --location \
  --request "GET" \
  --header "Accept: application/json" \
  --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
  --url "https://fastq.prod.umccr.org/api/v1/rgid/CAAGCTAG+CGCTATGT.2.241024_A00130_0336_BHW7MVDSXC"
```

Gives

```shell
{
  "id": "fqr.01JQ3BEM14JA78EQBGBMB9MHE4",
  "fastqSetId": "fqs.01JQ3BEM5FMGQ39GQCNXKFAXP4",
  "index": "CAAGCTAG+CGCTATGT",
  "lane": 2,
  "instrumentRunId": "241024_A00130_0336_BHW7MVDSXC",
  "library": {
    "orcabusId": "lib.01JBB5Y3QGZSGF74W6CTV0JJ16",
    "libraryId": "L2401544"
  },
  "platform": "Illumina",
  "center": "UMCCR",
  "date": "2024-10-24T00:00:00",
  "readSet": {
    "r1": {
      "ingestId": "0197614c-ba80-7773-8085-50ffd7dc6e99",
      "gzipCompressionSizeInBytes": null,
      "rawMd5sum": null
    },
    "r2": {
      "ingestId": "0197614c-bb5d-7a82-9177-783b478fedb4",
      "gzipCompressionSizeInBytes": null,
      "rawMd5sum": null
    },
    "compressionFormat": "ORA"
  },
  "qc": {
    "insertSizeEstimate": 286.0,
    "rawWgsCoverageEstimate": 5.54,
    "r1Q20Fraction": 0.98,
    "r2Q20Fraction": 0.96,
    "r1GcFraction": 0.41,
    "r2GcFraction": 0.41,
    "duplicationFractionEstimate": 0.31
  },
  "ntsm": {
    "ingestId": "0195ca99-4d67-7640-9f37-28a66ec51782"
  },
  "readCount": 56913395,
  "baseCountEst": 17187845290,
  "isValid": true
}
```

</details>

## Get Fastq Sets (api/v1/fastqSet)

What if we want a collection of fastqs, i.e all fastqs for a library AND its topup?

We can use the fastq set endpoint to retrieve all fastqs for a library.

Like the fastq endpoint, we can use any combination of lab metadata query parameters and
instrument run id to filter the results.

For any given library id, there is, at any given time, a maximum of one fastq set object that has the isCurrentFastqSet flag set to true.

When querying, the currentFastqSet flag is set to true by default.

<details>

<summary>Click to expand!</summary>

```shell
LIBRARY_ID="LPRJ250441"
curl \
  --fail --silent --show-error --location \
  --request "GET" \
  --header "Accept: application/json" \
  --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
  --url "https://fastq.prod.umccr.org/api/v1/fastqSet?library=${LIBRARY_ID}" | \
jq --raw-output \
  '.results'
```

Gives

> Notice that the s3 uris are missing, since we didn't set the `includeS3Details` query parameter.

```
[
  {
    "id": "fqs.01JR42NCZ8QQ1PVE4ANV4KCAM5",
    "library": {
      "orcabusId": "lib.01JP2JZ00NABRM8K3E1E8T4WXB",
      "libraryId": "LPRJ250441"
    },
    "fastqSet": [
      {
        "id": "fqr.01JR42NCWXRYJANXA1JXQCK9NC",
        "fastqSetId": "fqs.01JR42NCZ8QQ1PVE4ANV4KCAM5",
        "index": "GAATCCGA+AGCTAGTG",
        "lane": 4,
        "instrumentRunId": "250404_A00130_0362_AHFJ2FDSXF",
        "library": {
          "orcabusId": "lib.01JP2JZ00NABRM8K3E1E8T4WXB",
          "libraryId": "LPRJ250441"
        },
        "platform": "Illumina",
        "center": "UMCCR",
        "date": "2025-04-04T00:00:00",
        "readSet": {
          "r1": {
            "ingestId": "01961a45-424e-7d92-bd07-1510ad45b274",
            "gzipCompressionSizeInBytes": 28422256033,
            "rawMd5sum": "613b86c89d863db798858125b72abcf2"  // pragma: allowlist secret
          },
          "r2": {
            "ingestId": "01961a45-4e66-7111-a8a4-cc2d3a766e81",
            "gzipCompressionSizeInBytes": 28634551684,
            "rawMd5sum": "08778a7043f74c646594ed1e61726c7b"  // pragma: allowlist secret
          },
          "compressionFormat": "ORA"
        },
        "qc": null,
        "ntsm": null,
        "readCount": 380872149,
        "baseCountEst": 115023388998,
        "isValid": true
      },
      {
        "id": "fqr.01JRKRGF6RXZEGAQVMJRMFYDMR",
        "fastqSetId": "fqs.01JR42NCZ8QQ1PVE4ANV4KCAM5",
        "index": "GAATCCGA+AGCTAGTG",
        "lane": 1,
        "instrumentRunId": "250410_A00130_0365_BHFH2CDSXF",
        "library": {
          "orcabusId": "lib.01JP2JZ00NABRM8K3E1E8T4WXB",
          "libraryId": "LPRJ250441"
        },
        "platform": "Illumina",
        "center": "UMCCR",
        "date": "2025-04-10T00:00:00",
        "readSet": {
          "r1": {
            "ingestId": "01963a92-e77d-7253-9c84-79ddd949fe37",
            "gzipCompressionSizeInBytes": 28993974534,
            "rawMd5sum": "5cd7ff3d1c2228ea6017e40fffd10a7b"  // pragma: allowlist secret
          },
          "r2": {
            "ingestId": "01963a92-fe68-7cd0-8195-170b43a39ef2",
            "gzipCompressionSizeInBytes": 29563031530,
            "rawMd5sum": "7782d6be9e181b65ece9fc0b73eb8096"  // pragma: allowlist secret
          },
          "compressionFormat": "ORA"
        },
        "qc": null,
        "ntsm": null,
        "readCount": 385354912,
        "baseCountEst": 116377183424,
        "isValid": true
      }
    ],
    "allowAdditionalFastq": false,
    "isCurrentFastqSet": true
  }
]
```

</details>

## Run Jobs on Fastqs

The Fastq Manager can run jobs on fastqs to perform various calculations and estimations, for a given fastq id,
this includes:

- QC Stats (:runQcStats)
- Gzip file size estimation & Raw md5sum calculation (:runFileCompressionInformation)
- NTSM fingerprint calculation (:runNtsm)
- Read count + base count estimation (:runReadCount)

The QC stats for a given fastq can be calculated by using the `api/v1/fastq/<fastqId>:` endpoint.

```
curl \
  --fail --silent --show-error --location \
  --request "PATCH" \
  --header "Accept: application/json" \
  --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
  --header "Content-Type: application/json" \
  --url "https://fastq.dev.umccr.org/api/v1/fastq/fqr.01JQ3BEM14JA78EQBGBMB9MHE4:runQcStats" | \
jq --raw-output
```

Which returns the response

```json5
{
  id: 'fqj.01K03SVRA74ZZJ5SYW4NPZ7BCY',
  fastqId: 'fqr.01JQ3BEM14JA78EQBGBMB9MHE4',
  jobType: 'QC',
  stepsExecutionArn: 'arn:aws:states:ap-southeast-2:843407916570:execution:fastq-manager-runQcStats:edc0cb04-dfa8-4826-9e1d-e267b537338f',
  status: 'RUNNING',
  startTime: '2025-07-14T06:27:24.103115Z',
  ttl: 1753079244,
  endTime: null,
}
```

Currently, jobs can only be queried by the fastq id.

Once the job has completed, the fastq object will be updated with the new QC stats.

The fastq object will release an event on any update.

## Creating Fastq Objects

Fastqs are automatically created when a sequencer run is completed, thanks to the [Fastq Glue Service](https://github.com/OrcaBus/service-fastq-glue)

However, for external libraries, we may wish to create fastq objects manually.

To create a fastq object, you can use the `api/v1/fastq` endpoint with a POST request.

The request body will require the following fields:

<details>

<summary>Click to expand!</summary>

```json5
{
  // The index for the fastq (str)
  index: 'AAAAAAAA+GGGGGGGGG',
  // Lane (int)
  lane: 1,
  // instrumentRunId (str)
  instrumentRunId: '241024_A00130_0336_BHW7MVDSXC',
  // Library object (just the library Id is fine, orcabus Id will be automatically populated)
  library: {
    // Library Id (str)
    libraryId: 'L2401544',
  },
  // Platform - must be hardcoded to "Illumina" for now
  platform: 'Illumina',
  // Center - must be hardcoded to "UMCCR" for now
  center: 'UMCCR',
  // Date - should match the instrument run id date
  date: '2024-10-24',
  // ReadSet object
  // For each readset object, we do not need the ingestId,
  // Instead we can provide the s3Uri and the endpoint will automatically calculate the ingestId
  readSet: {
    // R1 read object
    // R1 read object should be in either ora or gzipped format
    // but ideally ORA format
    r1: {
      s3Uri: 's3://bucket/path/to/r1.fastq.ora',
    },
    r2: {
      s3Uri: 's3://bucket/path/to/r2.fastq.ora', // Optional, can be null if not available
    },
    compressionFormat: 'ORA', // Optional, can be null if not available
  },
  // Must be set to true
  isValid: true,
}
```

</details>

It is usually more preferable to create fastq sets, since the fastq set id is often the starting point for an analysis.

To create a fastq set, you can use the `api/v1/fastqSet` endpoint with a POST request.

The request body will require the following fields:

```json5
{
  // The library object, like above, just the library id is fine
  library: {
    libraryId: 'L2401544',
  },
  fastqSet: [
    // An array of fastq objects, identical to that placed in the example above
    // ...
  ],
}
```

By creating the fastq set instead of the fastq, a fastq set id will be generated, along with a fastq id, and the two objects will be linked.

## Deleting Fastq Objects

From time to time we may need to delete fastq objects.
An example of this is if the wrong index is used on the sequencer.
The index attribute to a fastq object is immutable, so if the index is wrong, we need to delete the fastq object and recreate it with the correct index.

Deleting a fastq object can be done by using the `api/v1/fastq/<fastqId>` endpoint with a DELETE request.

Only fastqs that do not belong to a fastq set can be deleted, hence the `api/v1/fastqSet/<fastqSetId>/unlinkFastq/<fastqId>` endpoint
is used to delete fastqs that belong to a fastq set.

## Amending Fastqs

From time to time, we may also need to amend fastq objects.

This might be the case if we need to update the read set, or the read set compression format.

An example of this is if BCLConvert has been rerun for a new instrument run id and therefore there is a new set of outputs.

This sample may not have been affected, and therefore has the same index and lane attributes, but the read set ingest ids now point to the deprecated data.

We can instead amend the read set to point to the new identical data for this fastq object.

## Amending Fastq Sets

From time to time, we may also need to amend fastq sets.

An example of this is if we need to add a new fastq to the fastq set (in the case of a topup library).

We may also need to set the currentFastqSet to False, in the case of a rerun, to make way for the new fastq set to be
the current fastq set for a given library.

Workflow

Dragen pipelines will use a fastqListRows as input (list of objects). We can generate this list by using a GET
request on either the `api/v1/fastq/<fastq_id>toFastqListRow` (single object) or `api/v1/fastqSet/<fastq_set_id>toFastqListRows` (list of objects) endpoints.

An example may be

<details>

<summary>Click to expand!</summary>

```shell
curl \
  --fail --silent --show-error --location \
  --request "GET" \
  --header "Accept: application/json" \
  --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
  --url "https://fastq.prod.umccr.org/api/v1/fastqSet/fqs.01JR42NCZ8QQ1PVE4ANV4KCAM5/toFastqListRows" | \
jq --raw-output
```

Gives

```json5
[
  {
    rgid: 'GAATCCGA+AGCTAGTG.4.250404_A00130_0362_AHFJ2FDSXF',
    rglb: 'LPRJ250441',
    rgsm: 'LPRJ250441',
    lane: 4,
    rgcn: 'UMCCR',
    rgds: 'Library ID: LPRJ250441, Sequenced on 4 Apr, 2025 at UMCCR, Assay: BM-6L, Type: BiModal',
    rgdt: '2025-04-04T00:00:00',
    rgpl: 'Illumina',
    read1FileUri: 's3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/ora-compression/250404_A00130_0362_AHFJ2FDSXF/20250409dfb45a6f/Samples/Lane_4/LPRJ250441/LPRJ250441_S20_L004_R1_001.fastq.ora',
    read2FileUri: 's3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/ora-compression/250404_A00130_0362_AHFJ2FDSXF/20250409dfb45a6f/Samples/Lane_4/LPRJ250441/LPRJ250441_S20_L004_R2_001.fastq.ora',
  },
  {
    rgid: 'GAATCCGA+AGCTAGTG.1.250410_A00130_0365_BHFH2CDSXF',
    rglb: 'LPRJ250441',
    rgsm: 'LPRJ250441',
    lane: 1,
    rgcn: 'UMCCR',
    rgds: 'Library ID: LPRJ250441 / Sequenced on 10 Apr 2025 at UMCCR / Assay: BM-6L / Type: BiModal',
    rgdt: '2025-04-10',
    rgpl: 'Illumina',
    read1FileUri: 's3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/ora-compression/250410_A00130_0365_BHFH2CDSXF/20250415299995d7/Samples/Lane_1/LPRJ250441/LPRJ250441_S1_L001_R1_001.fastq.ora',
    read2FileUri: 's3://pipeline-prod-cache-503977275616-ap-southeast-2/byob-icav2/production/ora-compression/250410_A00130_0365_BHFH2CDSXF/20250415299995d7/Samples/Lane_1/LPRJ250441/LPRJ250441_S1_L001_R2_001.fastq.ora',
  },
]
```

</details>

## For Download / Streaming

We can also generate 7-day length presigned urls for our fastq files, which can be used for downloading or streaming.

<details>

<summary>Click to expand!</summary>

```shell
curl \
  --fail --silent --show-error --location \
  --request "GET" \
  --header "Accept: application/json" \
  --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
  --url "https://fastq.dev.umccr.org/api/v1/fastq/fqr.01JQ3BEM14JA78EQBGBMB9MHE4/presign" | \
jq --raw-output
```

Gives

```json5
{
  r1: {
    s3Uri: 's3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/primary/241024_A00130_0336_BHW7MVDSXC/20250611c473883f/Samples/Lane_2/L2401544/L2401544_S12_L002_R1_001.fastq.ora',
    // Obviously I'm not going to put this in a README
    // since I don't want to have to deal with the paperwork
    presignedUrl: 'https://pipeline-...',
    expiresAt: '2025-07-21T06:50:52Z',
  },
  r2: {
    s3Uri: 's3://pipeline-dev-cache-503977275616-ap-southeast-2/byob-icav2/development/primary/241024_A00130_0336_BHW7MVDSXC/20250611c473883f/Samples/Lane_2/L2401544/L2401544_S12_L002_R2_001.fastq.ora',
    presignedUrl: '...',
    expiresAt: '2025-07-21T06:50:53Z',
  },
}
```

</details>

## Comparing Fastqs within a fastq set

For our LPRJ250441 library above, that has been run over two sequencing runs,
we may want to confirm that the fastqs are similar enough to be considered the same individual.

We can do this with our NTSM service.

We assume that the `:runNtsm` patch endpoint has been run for all fastqs in the fastq set.

We can then compare the fastqs internally with the following GET request:

This runs an 'express' step function to validate

<details>

<summary>Click to expand!</summary>

```shell
curl \
  --fail --silent --show-error --location \
  --request "GET" \
  --header "Accept: application/json" \
  --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
  --url "https://fastq.prod.umccr.org/api/v1/fastqSet/fqs.01JR42NCZ8QQ1PVE4ANV4KCAM5:validateNtsmInternal" | \
jq --raw-output
```

Gives

```json5
{
  // FIXME - Might need to pick a better example
  related: null,
}
```

</details>

## Comparing Two Fastq Sets

You may want to compare a tumor and normal library to confirm that they are from the same individual.

We can again do this with our NTSM service.

```shell
# This is a made up id, replace with your own
FASTQ_SET_ID_A="fqs.01JR42NCZ8QQ1PVE4ANV4KCAM5"
# This is a made up id, replace with your own
FASTQ_SET_ID_B="fqs.01JR42NCZ8QQ1PVE4ANV4KCAM6"
curl \
  --fail --silent --show-error --location \
  --request "GET" \
  --header "Accept: application/json" \
  --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
  --url "https://fastq.prod.umccr.org/api/v1/fastqSet/${FASTQ_SET_ID_A}:validateNtsmExternal/${FASTQ_SET_ID_B}" | \
jq --raw-output
```

## MultiQC Summaries

If fastqs have qc results, we can generate a combined multiqc summary.

The following example goes through:

1. Finding all fastqs in an instrument run id (241024_A00130_0336_BHW7MVDSXC)
2. Determining which fastq need QC stats and running those jobs.
3. Generating a multiqc summary for all fastqs in the instrument run id.

### Get all fastqs

<details>

<summary>Click to expand!</summary>

```shell
INSTRUMENT_RUN_ID="241024_A00130_0336_BHW7MVDSXC"
all_fastq_objects="$( \
  curl \
    --fail --silent --show-error --location \
    --request "GET" \
    --header "Accept: application/json" \
    --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
    --url "https://fastq.dev.umccr.org/api/v1/fastq?instrumentRunId=${INSTRUMENT_RUN_ID}" | \
  jq --raw-output \
    '
      .results
    ' \
)"
```

</details>

### Get missing QC stats

<details>

<summary>Click to expand!</summary>

```shell
missing_qc_fastq_id_list="$( \
  jq --raw-output \
    '
      map(
        select(
          .qc == null or
          .qc.sequaliReports.multiqcParquet == null
        ) |
        .id
      )[]
    ' \
    <<< "${all_fastq_objects}" \
)"

for fastq_id in $(echo ${missing_qc_fastq_id_list}); do
  curl \
    --fail --silent --show-error --location \
    --request "PATCH" \
    --header "Accept: application/json" \
    --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
    --url "https://fastq.dev.umccr.org/api/v1/fastq/${fastq_id}:runQcStats"
done
```

</details>

### Generate MultiQC Summary

Reconfirm all fastqs now have QC stats with MultiQC Parquet files present,

Then launch MultiQC summary generation.

<details>

```shell
curl \
  --fail --silent --show-error --location \
  --request "POST" \
  --header "Accept: application/json" \
  --header "Authorization: Bearer ${ORCABUS_TOKEN}" \
  --header "Content-Type: application/json" \
  --data "$(
    jq --raw-output 'map(.id)' <<< "${all_fastq_objects}" \
  )" \
  --url "https://fastq.dev.umccr.org/api/v1/multiqc"
```

</details>
