#!/usr/bin/env python3

"""
Use the boto3 api to discover the services running in the AWS account.

SERVICE NAME is 'fingerprint'
"""

# Imports
import typing
import boto3

# Type checking imports
if typing.TYPE_CHECKING:
    from mypy_boto3_servicediscovery import ServiceDiscoveryClient


def get_service_discovery_client() -> 'ServiceDiscoveryClient':
    return boto3.client('servicediscovery')


def handler(event, context):
    """
    Get the cloudmap service
    :return:
    """
    service_name = event['serviceName']

    service_discovery_client = get_service_discovery_client()

    service_object = next(
        filter(
            lambda service_iter_: service_iter_['Name'] == service_name,
            service_discovery_client.list_services()['Services']
        )
    )

    return {
        "serviceObj": {
            "serviceId": service_object['Id'],
            "serviceName": service_object['Name'],
            "serviceArn": service_object['Arn'],
        }
    }
