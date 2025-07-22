#!/usr/bin/env python3

"""
Update multiqc job status in the database.
"""

# Update multiqc job status in the database
from orcabus_api_tools.fastq import update_multiqc_job_status


def handler(event, context):
    """
    Lambda function handler to update multiqc job status.
    :param event:
    :param context:
    :return:
    """
    # Update multiqc job status
    job_id = event.get('jobId')
    status = event.get('status')
    html_output_uri = event.get('htmlOutputUri', None)  # Only if status is 'SUCCEEDED'
    parquet_output_uri = event.get('parquetOutputUri', None)  # Only if status is 'SUCCEEDED'

    # Update multiqc job status
    update_multiqc_job_status(
        job_id=job_id,
        status=status,
        html_output_uri=html_output_uri,
        parquet_output_uri=parquet_output_uri
    )


if __name__ == '__main__':
    import json
    from os import environ
    environ['AWS_PROFILE'] = 'umccr-development'
    environ['HOSTNAME_SSM_PARAMETER_NAME'] = '/hosted_zone/umccr/name'
    environ['ORCABUS_TOKEN_SECRET_ID'] = 'orcabus/token-service-jwt'

    print(json.dumps(
        handler(
            {
                "jobId": "mqj.01K0QSGW4TNKZH9AD3Z4JRR1P2",
                "status": "SUCCEEDED",
                "htmlOutputUri": "s3://fastq-manager-sequali-outputs-843407916570-ap-southeast-2/multiqc-html/year=2025/month=07/day=22/76432625-a540-4bc0-9084-7f960c5b7100/multiqc_output.html",
                "parquetOutputUri": "s3://fastq-manager-sequali-outputs-843407916570-ap-southeast-2/multiqc-html/year=2025/month=07/day=22/76432625-a540-4bc0-9084-7f960c5b7100/multiqc_output.parquet"
            },
            None
        ),
        indent=4
    ))
