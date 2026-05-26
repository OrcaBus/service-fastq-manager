#!/usr/bin/env python3

"""
Evaluate the ntsm for two files
"""

# Standard imports
from io import StringIO
from pathlib import Path
from subprocess import run
import typing
import boto3
from urllib.parse import urlparse
from typing import Tuple
from tempfile import NamedTemporaryFile
import pandas as pd

# Set up logging
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


def get_s3_client() -> 'S3Client':
    """
    Get the s3 client
    :return:
    """
    return boto3.client('s3')


def get_bucket_key_from_uri(s3_uri: str) -> Tuple[str, str]:
    s3_obj = urlparse(s3_uri)

    return s3_obj.netloc, s3_obj.path.lstrip("/")


def download_s3_file_to_tmp(s3_client: 'S3Client', s3_uri: str) -> Path:
    """
    Download a file from s3 to a temporary file
    :param s3_client:
    :param s3_uri:
    :return:
    """
    bucket, key = get_bucket_key_from_uri(s3_uri)

    with NamedTemporaryFile(delete=False) as tmp_file:
        s3_client.download_fileobj(bucket, key, tmp_file)
        tmp_file_path = Path(tmp_file.name)

    return tmp_file_path


def handler(event, context):
    """
    Collect the two ntsm files
    :param event:
    :param context:
    :return:
    """
    s3 = get_s3_client()
    s3_uri_a = event['ntsmS3UriA']
    s3_uri_b = event['ntsmS3UriB']

    # Download the files
    ntsm_file_a = download_s3_file_to_tmp(s3, s3_uri_a)
    ntsm_file_b = download_s3_file_to_tmp(s3, s3_uri_b)

    # Evaluate the files
    eval_proc = run(
        ['ntsmEval', "--all", ntsm_file_a, ntsm_file_b],
        capture_output=True
    )

    # Check if the evaluation was successful
    relatedness_df = pd.read_csv(StringIO(eval_proc.stdout.decode('utf-8')), sep="\t")

    # If the combined coverage is less than 1.5, we cannot determine the relatedness
    coverage = relatedness_df['cov1'].item() + relatedness_df['cov2'].item()
    if coverage < 1.5:
        logger.info(f"Not enough coverage in samples to determine relatedness. Got {coverage}, need at least 1.5")
        return {
            "undetermined": True,
            "relatedness": None,
            "score": relatedness_df["score"].item(),
            "sameSample": None
        }

    if relatedness_df["same"].item() == 1:
        return {
            "undetermined": False,
            "relatedness": relatedness_df["relate"].item(),
            "score": relatedness_df["score"].item(),
            "sameSample": True
        }
    else:
        return {
            "undetermined": False,
            "relatedness": relatedness_df["relate"].item(),
            "score": relatedness_df["score"].item(),
            "sameSample": False
        }
