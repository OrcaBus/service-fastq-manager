#!/usr/bin/env python3

"""
Use the boto3 api to list a service's instances
"""

import typing
import boto3

if typing.TYPE_CHECKING:
    from mypy_boto3_servicediscovery import ServiceDiscoveryClient


def get_service_discovery_client() -> 'ServiceDiscoveryClient':
    return boto3.client('servicediscovery')


def handler(event, context):
    """
    Get the service id
    :return:
    """
    service_id = event["serviceId"]

    service_discovery_client = get_service_discovery_client()

    service_instances = list(
        map(
            lambda service_instance_iter_: {
              "instanceId": service_instance_iter_['Id'],
              "instanceAttributes": list(
                  map(
                    lambda instance_kv_iter_: {
                        "attrKey": instance_kv_iter_[0],
                        "attrValue": instance_kv_iter_[1],
                    },
                    service_instance_iter_['Attributes'].items()
                  )
              ),
            },
            service_discovery_client.list_instances(ServiceId=service_id)['Instances']
        )
    )

    return {
        "serviceInstances": service_instances
    }
