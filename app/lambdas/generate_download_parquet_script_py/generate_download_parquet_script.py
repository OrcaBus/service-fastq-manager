#!/usr/bin/env python3

"""
Generate a shell script that downloads a bunch of multiqc parquet files.

Inputs:
  * fastqIdList
  * downloadParquetScriptUri

Steps:

* Convert the fastq ids to a list of ingest ids
* For each ingest id, use the file manager to generate a presigned url of the parquet file
* Write the urls to a shell script that can be run to download the parquet files in parallel.
* The script will use wget to download the files in parallel

There are no outputs for this step since the script is written to a file provided by the inputs
"""
from os import environ
# Standard library imports
from pathlib import Path
from textwrap import dedent
from typing import List, Dict
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
import boto3
import typing

# Imports
from orcabus_api_tools.fastq import get_fastq
from orcabus_api_tools.filemanager import get_presigned_urls_from_ingest_ids

# Typing imports
if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


def get_s3_client() -> 'S3Client':
    return boto3.client('s3')


def get_ingest_id_from_fastq_id(fastq_id):
    """
    Convert a fastq id to an ingest id.
    """
    fastq_obj = get_fastq(
        fastq_id
    )

    return fastq_obj['qc']['sequaliReports']['multiqcParquet']['ingestId']


def write_script(
        presigned_urls_dict_list: List[Dict[str, str]],
        output_file_path: Path
):
    """
    Presigned urls dict, which is a dictionary of ingest ids to presigned urls,
    :param presigned_urls_dict_list:
    :param output_file_path:
    :return:
    """
    create_directories_script_list = "& \\\n".join(
        list(map(
            lambda
                presigned_url_list_iter_: f"mkdir -p \"${{download_path}}/{presigned_url_list_iter_['ingestId']}\"",
            presigned_urls_dict_list
        ))
    )

    wget_script_list = "& \\\n".join(
        list(map(
            lambda
                presigned_url_list_iter_: f"wget --output-document=\"${{download_path}}/{presigned_url_list_iter_['ingestId']}/multiqc.parquet\" \"{presigned_url_list_iter_['presignedUrl']}\"",
            presigned_urls_dict_list
        ))
    )

    shell_script = dedent(f"""
        #!/usr/bin/env bash

        # Set to fail
        set -euo pipefail

        # Get the download path parameter
        download_path="$1"

        # Create directory lists
        {create_directories_script_list} & \\
        wait

        # Download the parquet files in parallel
        {wget_script_list} & \\
        wait
    """)

    # Write the script to the file
    with open(output_file_path, 'w') as output_file_h:
        output_file_h.write(shell_script)


def upload_file_to_s3(
        local_file_path: Path,
        s3_uri: str
):
    # Get the bucket and key from the S3 URI
    s3_obj = urlparse(s3_uri)

    bucket = s3_obj.netloc
    key = s3_obj.path.lstrip('/')

    # Use boto3 to upload the file
    s3_client = get_s3_client()

    s3_client.upload_file(
        Filename=str(local_file_path.absolute()),
        Bucket=bucket,
        Key=key
    )


def handler(event, context):
    """
    Event handler
    :param event:
    :param context:
    :return:
    """

    # Get inputs
    fastq_id_list = event['fastqIdList']
    download_parquet_script_uri = event['downloadParquetScriptUri']

    # Create the local output path
    output_file_path = Path(NamedTemporaryFile(suffix='.sh', delete=False).name)

    # Convert fastq ids to ingest ids
    ingest_id_list = list(map(
        lambda fastq_id_iter_: get_ingest_id_from_fastq_id(fastq_id_iter_),
        fastq_id_list
    ))

    # Get presigned urls for the parquet files
    presigned_urls_dict = get_presigned_urls_from_ingest_ids(
        ingest_ids=ingest_id_list
    )

    # Write the urls to a shell script
    write_script(
        presigned_urls_dict_list=presigned_urls_dict,
        output_file_path=output_file_path
    )

    # Upload the script to the specified URI
    upload_file_to_s3(
        local_file_path=output_file_path,
        s3_uri=download_parquet_script_uri
    )


# if __name__ == '__main__':
#     import json
#     environ['AWS_PROFILE'] = 'umccr-development'
#     environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
#     environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'
#
#     print(json.dumps(
#         handler(
#             {
#                 "fastqIdList": [
#                     "fqr.01JQ3BEM14JA78EQBGBMB9MHE4"  # pragma: allowlist secret
#                 ],
#                 "downloadParquetScriptUri": "s3://fastq-manager-cache-843407916570-ap-southeast-2/cache/year=2025/month=07/day=21/aea6ac83-ea9c-4e02-8978-42b0693013e0/downloads.sh"
#             },
#             None
#         ),
#         indent=4
#     ))
