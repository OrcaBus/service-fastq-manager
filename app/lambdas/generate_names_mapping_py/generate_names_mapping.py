#!/usr/bin/env python3

"""
Generate the names mapping file for a multiqc report

The names mapping tsv file is used to map sample names to the names we want in the report

There is no header, just two columns:
original_name    new_name

Inputs:
* fastqIdList - the list of fastq IDs to process
* combineLibraryLanes - boolean indicating whether to combine library lanes if a given library is split across multiple lanes
* namesMappingTsvUri - the URI of the names mapping tsv file to upload to
"""

# Standard library imports
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
import boto3
import typing
import pandas as pd

# Imports
from orcabus_api_tools.fastq import get_fastq

# Typing imports
if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


def get_s3_client() -> 'S3Client':
    return boto3.client('s3')


def get_fastq_library_lane_df_from_fastq_id(fastq_id) -> pd.DataFrame:
    """
    Convert a fastq id to an ingest id.
    """
    fastq_obj = get_fastq(
        fastq_id
    )

    return pd.DataFrame([
        {
            "fastqId": fastq_obj['id'],
            "libraryId": fastq_obj['library']['libraryId'],
            "lane": fastq_obj['lane'],
        }
    ])


def write_tsv(
        fastq_sample_names_df: pd.DataFrame,
        output_file_path: Path
):
    """
    Presigned urls dict, which is a dictionary of ingest ids to presigned urls,
    :param fastq_sample_names_df:
    :param output_file_path:
    :return:
    """
    fastq_sample_names_df[[
        "fastqId", "libraryId"
    ]].to_csv(
        output_file_path,
        sep='\t',
        index=False
    )


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
    names_mapping_tsv_uri = event['namesMappingTsvUri']
    combine_library_lanes = event['combineLibraryLanes']

    # Create the local output path
    output_file_path = Path(NamedTemporaryFile(suffix='.tsv', delete=False).name)

    # Convert fastq ids to ingest ids
    fastq_df = pd.concat(
        list(map(
            lambda fastq_id_iter_: get_fastq_library_lane_df_from_fastq_id(fastq_id_iter_),
            fastq_id_list
        ))
    )

    # If we are combining library lanes, group by libraryId and take the first lane
    if not combine_library_lanes:
        fastq_df_list = []
        for library_id, library_df in fastq_df.groupby('libraryId'):
            if library_df.shape[0] > 1:
                # FIXME - could be across multiple runs so we should probably handle that here too)
                # We have multiple lanes for this library, so we will just extend the 'libraryId' attribute
                # To have 'L(lane_number)' appended to the libraryId
                library_df['libraryId'] = library_df.apply(
                    lambda library_lane_row_iter_: f"{library_lane_row_iter_['libraryId']} (L{str(library_lane_row_iter_['lane'])})",
                    axis="columns"
                )
            fastq_df_list.append(library_df)

        fastq_df = pd.concat(fastq_df_list)

    # Write the urls to a shell script
    write_tsv(
        fastq_sample_names_df=fastq_df,
        output_file_path=output_file_path
    )

    # Upload the script to the specified URI
    upload_file_to_s3(
        local_file_path=output_file_path,
        s3_uri=names_mapping_tsv_uri
    )


# if __name__ == '__main__':
#     from os import environ
#     import json
#
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
#                 "combineLibraryLanes": False,
#                 "namesMappingTsvUri": "s3://fastq-manager-cache-843407916570-ap-southeast-2/cache/year=2025/month=07/day=21/aea6ac83-ea9c-4e02-8978-42b0693013e0/names_mapping.tsv"
#             },
#             None
#         ),
#         indent=4
#     ))
