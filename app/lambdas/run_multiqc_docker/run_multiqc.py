#!/usr/bin/env python3

"""
Given a list of ingest ids, perform the following:

1. Call the file manager to get presigned urls for each ingest id

2. Download the files from the presigned urls

3. Run MultiQC on the downloaded files

4. Upload the MultiQC report to the fastq cache bucket
"""

# Standard library imports
from subprocess import run, CalledProcessError
from tempfile import TemporaryDirectory, NamedTemporaryFile
from pathlib import Path
from textwrap import dedent
import logging
import typing
from boto3 import client
import pandas as pd
from typing import List, Dict
from urllib.parse import urlparse
import json
import re

# Get logger
logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


# Globals
# In order for MultiQC to recognise the parquet file, it must be named this way
MULTIQC_PARQUET_FILENAME = "multiqc.parquet"

# Functions
def get_path_from_url(url):
    """
    Extracts the file name from a presigned URL.
    :param url: Presigned URL
    :return: Path object representing the file name
    """
    parsed_url = urlparse(url)
    return Path(parsed_url.path).name


def upload_to_s3(local_path: Path, s3_uri: str):
    """
    Uploads a file to S3.
    :param local_path: Local path of the file to upload
    :param s3_uri: S3 URI where the file should be uploaded
    """
    # Get the S3 client
    s3: 'S3Client' = client('s3')

    s3_obj = urlparse(s3_uri)
    bucket_name = s3_obj.netloc
    key = s3_obj.path.lstrip('/')

    try:
        s3.upload_file(
            Filename=str(local_path),
            Bucket=bucket_name,
            Key=key
        )
        logger.info(f"Uploaded {local_path} to {s3_uri}")
    except Exception as e:
        logger.error(f"Failed to upload {local_path} to {s3_uri}: {e}")
        raise


def generate_presigned_url(s3_uri: str):
    """
    Generate a presigned url for the given S3 URI.
    :param s3_uri:
    :return:
    """
    # Get the s3 client
    s3: 'S3Client' = client('s3')

    s3_obj = urlparse(s3_uri)
    bucket_name = s3_obj.netloc
    key = s3_obj.path.lstrip('/')

    return s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': bucket_name,
            'Key': key,
        }
    )


def generate_sample_names_mapping_tsv(
        fastq_id_list_to_library_id_list: List[Dict[str, str]]
) -> Path:
    """
    Generates a sample names mapping TSV from the fastq_id_list_to_library_id_list.
    :param fastq_id_list_to_library_id_list: List of dictionaries mapping fastq ids to library ids
    :return: Path to the generated TSV file
    """
    # Convert the list of dictionaries to a DataFrame
    mapping_df = pd.DataFrame(fastq_id_list_to_library_id_list)

    # Generate a temporary file for the TSV
    with NamedTemporaryFile(delete=False, mode='w', suffix='.tsv') as temp_file:
        mapping_df[['fastqId', 'libraryId']].to_csv(
            temp_file,
            sep='\t',
            header=False,
            index=False
        )

        return Path(temp_file.name)


def generate_download_presigned_urls_script(presigned_urls_list: List[str], output_dir):
    shell_script = dedent(
        f"""
        #!/usr/bin/env bash

        set -euo pipefail

        cd "{str(output_dir)}"
        """
    )

    for presigned_urls_item in presigned_urls_list:
        file_dir = re.sub(".parquet$", "", Path(urlparse(presigned_urls_item).path).name)
        shell_script += f"mkdir \"{file_dir}\"; wget --quiet --output-document \"{file_dir}/{MULTIQC_PARQUET_FILENAME}\" \"{presigned_urls_item}\" & \\\n"

    # Finish the script
    shell_script += "wait\n"

    with NamedTemporaryFile(suffix='.sh', delete=False) as temp_file:
        temp_file.write(shell_script.encode('utf-8'))

    return Path(temp_file.name)


def handler(event, context):
    """
    Lambda handler function to process MultiQC reports.
    :param event:
    :param context:
    :return:
    """

    # Get the ingest id list from the event
    fastq_id_list_to_library_id_list = event.get("fastqIdToLibraryIdList")
    presigned_url_list = event.get("presignedUrlList")

    # Get the output uri from the event
    output_uri = event.get("outputUri")

    # Create the temporary input directory
    input_temp_dir = Path(TemporaryDirectory(delete=False).name)

    # Create the output directory if it doesn't exist
    output_temp_dir = Path(TemporaryDirectory(delete=False).name)

    # Download presigned urls
    download_script = generate_download_presigned_urls_script(
        presigned_url_list, input_temp_dir
    )

    # Run the download script
    download_proc = run(["bash", str(download_script)])

    # Check if the download script ran successfully
    try:
        download_proc.check_returncode()
    except CalledProcessError as e:
        raise ValueError("Download script failed with non-zero exit code") from e

    # Generate the sample names mapping tsv
    samples_name_tsv = generate_sample_names_mapping_tsv(fastq_id_list_to_library_id_list)

    # Get all files in the temp dir
    input_files = list(input_temp_dir.rglob(f"*/{MULTIQC_PARQUET_FILENAME}"))

    # Step 3: Run MultiQC on the downloaded files
    multiqc_command = [
        "multiqc",
        "--sample-names", str(samples_name_tsv),
        "--outdir", str(output_temp_dir),
        *list(map(str, input_files))
    ]

    # Run the multiqc command
    multiqc_proc = run(multiqc_command)

    # Check if MultiQC ran successfully
    try:
        multiqc_proc.check_returncode()
    except CalledProcessError as e:
        logger.error("MultiQc failed with non-zero exit code")
        raise ValueError from e

    # Upload the MultiQC report to the fastq cache bucket
    upload_to_s3(
        output_temp_dir / "multiqc_report.html",
        output_uri
    )

    # Generate a presigned url for the multiqc report
    return {
        "presignedUrl": generate_presigned_url(output_uri)
    }


if __name__ == "__main__":
    from os import environ
    from datetime import datetime

    environ['AWS_PROFILE'] = 'umccr-development'
    environ['AWS_REGION'] = 'ap-southeast-2'

    # Test the handler function with a sample event
    print(datetime.now())
    print(
        json.dumps(
            handler(
                {
                    "presignedUrlList": [
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/859033e3-8aee-4e82-a3f4-9df0459003a3/fqr.01JQ3BEKYHYB1CBDK92X10CF3H.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=07f4f8c065404e9dc3bce5400941b915e163c7a4da79125fa40016b1acb946ad",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/167ad516-aa18-47b7-8e66-7416e6975096/fqr.01JQ3BEQK5MZ2G9WRCVQ22607C.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=34db598f81dd029138bf9c6a1b29676f8f271d3897e1bd15300cabcfd4d6890a",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/204510d4-3335-4a30-bb7a-e78795537907/fqr.01JQ3BETZ1J2T7FZCW4XMY9Y8N.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=90ea0ca7b58adfa8558ca04f753ce11d533a43bdeb03e4e73e631aabb0d7b095",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/84ae9d65-431c-44ef-bc2f-205eb9efdc56/fqr.01JQ3BEQH2JERY06QGM121XZYY.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=3f5c398595f4c5e857006d388243c5734889df967e94e8122b185abf27a5029c",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/85a98741-da86-40a2-8425-4c751c6d720e/fqr.01JQ3BETYS0D29J74RY32VNZ91.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=d2b4607635091cfc2e73f266843bf2adebe920d28d5600f4a391582dcb2a54f9",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/0d4943b8-7f31-4e66-a0e2-04e9705793f0/fqr.01JQ3BEQ4TE2A0S41C7TQVGDEH.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=b951ef9727c1f27816b7621e8297d2aaf7ffd655dbf060d7ff8490cbd44ed2c9",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/5396a3d0-e738-4195-865a-d6fc6efcadab/fqr.01JQ3BEPGWPAZGX57654BVF9C2.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=10bb0066dc446cb11606335e8ca11219abeba7834b48f5aa480a3e18370843d8",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/49c74f96-ea36-46b1-a72e-430984220c07/fqr.01JQ3BEQKTSHTXWN6A793MEQQF.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=b09496bcbffdc5fedf4e3bedb5c69ef0b93e297e08434797277b33ede9fa0678",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/8e0dc0b7-d3cd-457f-b318-3199dd1cbd7d/fqr.01JQ3BEQDRTX7PPTRV1G71PBAZ.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=a222c8758b23979c51997e44de482459cf2c209da75e9f10f6350098e3958a14",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/badbb105-94cc-4da2-a9dc-c16ce9db921a/fqr.01JQ3BETTR9JPV33S3ZXB18HBN.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=efaa17254fb893c913388e05dac441b46e17f8f3b56faf1a977e2e8141c48471",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/9bbe7d38-5f66-4e01-86f5-f6d4e1fe183e/fqr.01JQ3BEPSCXV6N3N8N92G6AEP9.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=913cdbed72eafcc05589080168e3e1146a9a3355903173c6da788e9bbdc995f5",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/db53d827-13cc-43ad-b210-96075bd4870a/fqr.01JQ3BEM3A51MEMNS93BBMX19K.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=f7bda98fcf45ff867ce6cb97ee4ca1af888efdd557e22753172da6bbe3a5eb13",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/2d4c0875-046a-4bcc-8dc8-35877d5b0fbd/fqr.01JQ3BEPRBJZT22RY40E4GPHC1.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=34a666800eb54b90511696bb2ad3ce2262dd74ff3cbb0025f3bb28bb9fca7e62",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/c43f3593-ee58-48d7-a94c-f80ffb69d352/fqr.01JQ3BEQ0QPF6EGE22J4SFGME9.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=2ec61473cb11c0f2837fa1155ab57ac8f86df753caf83e814e6291b714aa3264",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/d98065cf-d36b-49d2-94d6-4f8c6adc42ab/fqr.01JQ3BEPYMVFGGVAM18TG7FK3H.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=6f39121f4e6ebb4a845382f931d4582d55c7c2de3deb1da33331f9235d69cd80",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/ce0df202-e2c5-4949-b3b2-b5bb2579f7ca/fqr.01JQ3BETJ1NPT84524JZCNKWDW.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=90e78e913d14ab220693420bfff21487dc145b84fdccc314db34aa3846509fd0",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/1bbed33b-80e6-415a-a51d-018c329d901e/fqr.01JQ3BEKVPTRZQWS1G99ZHNW1J.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=2768ee58b934bdea01324a140a5576f4d0bc1e8fd0109fe515a58d1c2e83acd3",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/dcf4fef1-a40e-406a-a7ef-9e502a06a835/fqr.01JQ3BEPXTCR45FC976CX42FGM.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=4a8b94aa60063e94ff86d22f8db6ae6e1fbdc9acbc5a56d373a6cda0e0a0680a",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/3577372c-a21c-4c7f-a0ee-b257369d7a1e/fqr.01JQ3BETVERZS6XKNBYY2FZRH5.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=747e0640f6d8bda6e74144e1e4e061873da4774e1d46134259155df16b2b07d8",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/ab313512-1fb1-4deb-9799-9c3d9b883f67/fqr.01JQ3BEQM10G01958TBR74XWGG.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=3b04024978236361bfca470e79ac102cbf064982dd7ab9aae69f3bdaf0589927",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/de58bd5e-3fa8-40ec-8d1c-2e2c733748ab/fqr.01JQ3BEKXFR0SV2ZSB6SAKJJZP.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=fae886af583071cb72b791567b877a5c1e16a82bfc2e64c001282d5ff4ffcbe0",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/031748f2-9eaa-4a88-854e-a396fda188c1/fqr.01JQ3BEM25HYPN9NSBKXQHKKEW.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=8d2cedf356a924c13b3bc185b40cd408104f1f9064e50d1332b8eeac31911d00",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/9bb9b298-3851-46eb-ad3e-9d0d69484ddb/fqr.01JQ3BETXWZTH4NWESCJCX1YS2.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=03a51822c11ee8925f0ec48ec7e80250bbf587649335879df1841b099834f73e",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/09076e0c-5f86-4686-89e8-f81ffcf9576f/fqr.01JQ3BEQE2E59WG51CSPJS3Q4V.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=1fbd8925f2061bf87e66fdad489c934fe61cf3c89d0d9a6a5108859af92be3e2",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/2b1bc47a-ccd5-42f7-a9a7-1d8855f864f0/fqr.01JQ3BEM28CXBXG8CT578BH8BW.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=8dbf682184f93ae60f6f9dce68534ca2590d41ea52ed8b061570431aa7ee15db",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/ade039d8-19e9-413c-ba29-189600d75f4b/fqr.01JQ3BEM14JA78EQBGBMB9MHE4.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=614c637161905243dc2764118eb4653770546e41232fc453dac4d79473f3752d",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D18/551c332f-6ae7-4658-a575-bb020ef9112e/fqr.01JQ3BETMJ4EF6N3PYJAHM7T3G.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=0357e31442c17e0802b66de38e8614d1ebc561436c6f5340ff89ef97aa121e8f",
                        "https://fastq-manager-sequali-outputs-843407916570-ap-southeast-2.s3.ap-southeast-2.amazonaws.com/multiqc-parquet/year%3D2025/month%3D07/day%3D17/cfc96102-950b-4ddb-bb05-4b10e2399300/fqr.01JQ3BEKS05C74XWT5PYED6KV5.parquet?x-id=GetObject&response-content-disposition=inline&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIA4IXYHPYNOGA2556J%2F20250718%2Fap-southeast-2%2Fs3%2Faws4_request&X-Amz-Date=20250718T053536Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=7c78beb6eb3740bde22139002e6e35780c13221224a05f10b2d10c637a010886"
                    ],
                    "fastqIdToLibraryIdList": [
                        {
                            "libraryId": "L2401541",
                            "fastqId": "fqr.01JQ3BEKYHYB1CBDK92X10CF3H"
                        },
                        {
                            "libraryId": "L2401535",
                            "fastqId": "fqr.01JQ3BEQK5MZ2G9WRCVQ22607C"
                        },
                        {
                            "libraryId": "L2401531",
                            "fastqId": "fqr.01JQ3BETZ1J2T7FZCW4XMY9Y8N"
                        },
                        {
                            "libraryId": "L2401532",
                            "fastqId": "fqr.01JQ3BEQH2JERY06QGM121XZYY"
                        },
                        {
                            "libraryId": "L2401552",
                            "fastqId": "fqr.01JQ3BETYS0D29J74RY32VNZ91"
                        },
                        {
                            "libraryId": "L2401539",
                            "fastqId": "fqr.01JQ3BEQ4TE2A0S41C7TQVGDEH"
                        },
                        {
                            "libraryId": "L2401527",
                            "fastqId": "fqr.01JQ3BEPGWPAZGX57654BVF9C2"
                        },
                        {
                            "libraryId": "L2401534",
                            "fastqId": "fqr.01JQ3BEQKTSHTXWN6A793MEQQF"
                        },
                        {
                            "libraryId": "L2401549",
                            "fastqId": "fqr.01JQ3BEQDRTX7PPTRV1G71PBAZ"
                        },
                        {
                            "libraryId": "L2401548",
                            "fastqId": "fqr.01JQ3BETTR9JPV33S3ZXB18HBN"
                        },
                        {
                            "libraryId": "L2401546",
                            "fastqId": "fqr.01JQ3BEPSCXV6N3N8N92G6AEP9"
                        },
                        {
                            "libraryId": "L2401544",
                            "fastqId": "fqr.01JQ3BEM3A51MEMNS93BBMX19K"
                        },
                        {
                            "libraryId": "L2401547",
                            "fastqId": "fqr.01JQ3BEPRBJZT22RY40E4GPHC1"
                        },
                        {
                            "libraryId": "L2401537",
                            "fastqId": "fqr.01JQ3BEQ0QPF6EGE22J4SFGME9"
                        },
                        {
                            "libraryId": "L2401528",
                            "fastqId": "fqr.01JQ3BEPYMVFGGVAM18TG7FK3H"
                        },
                        {
                            "libraryId": "L2401530",
                            "fastqId": "fqr.01JQ3BETJ1NPT84524JZCNKWDW"
                        },
                        {
                            "libraryId": "L2401540",
                            "fastqId": "fqr.01JQ3BEKVPTRZQWS1G99ZHNW1J"
                        },
                        {
                            "libraryId": "L2401536",
                            "fastqId": "fqr.01JQ3BEPXTCR45FC976CX42FGM"
                        },
                        {
                            "libraryId": "L2401533",
                            "fastqId": "fqr.01JQ3BETVERZS6XKNBYY2FZRH5"
                        },
                        {
                            "libraryId": "L2401499",
                            "fastqId": "fqr.01JQ3BEQM10G01958TBR74XWGG"
                        },
                        {
                            "libraryId": "L2401553",
                            "fastqId": "fqr.01JQ3BEKXFR0SV2ZSB6SAKJJZP"
                        },
                        {
                            "libraryId": "L2401526",
                            "fastqId": "fqr.01JQ3BEM25HYPN9NSBKXQHKKEW"
                        },
                        {
                            "libraryId": "L2401543",
                            "fastqId": "fqr.01JQ3BETXWZTH4NWESCJCX1YS2"
                        },
                        {
                            "libraryId": "L2401529",
                            "fastqId": "fqr.01JQ3BEQE2E59WG51CSPJS3Q4V"
                        },
                        {
                            "libraryId": "L2401545",
                            "fastqId": "fqr.01JQ3BEM28CXBXG8CT578BH8BW"
                        },
                        {
                            "libraryId": "L2401544",
                            "fastqId": "fqr.01JQ3BEM14JA78EQBGBMB9MHE4"
                        },
                        {
                            "libraryId": "L2401542",
                            "fastqId": "fqr.01JQ3BETMJ4EF6N3PYJAHM7T3G"
                        },
                        {
                            "libraryId": "L2401538",
                            "fastqId": "fqr.01JQ3BEKS05C74XWT5PYED6KV5"
                        }
                    ],
                    "outputUri": "s3://fastq-manager-cache-843407916570-ap-southeast-2/multiqc-cache/year=2025/month=07/day=18/2173e05a-e6c2-41ff-8dd9-da00113dce82/multiqc_output.html"
                },
                None
            ),
            indent=2,
        )
    )
    print(datetime.now())

    # {
    #   "presignedUrlList": [
    #     "https://fastq-manager-sequali-outputs..."
    #   ]
    # }
