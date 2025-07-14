#!/usr/bin/env python3
import json
import typing
from typing import Dict, Union
from os import environ

import boto3

from ..globals import (
    EVENT_BUS_NAME_ENV_VAR,
    EVENT_SOURCE_ENV_VAR,
    EVENT_DETAIL_TYPE_FASTQ_STATE_CHANGE_ENV_VAR,
    EVENT_DETAIL_TYPE_FASTQ_SET_STATE_CHANGE_ENV_VAR,
    FastqStateChangeStatusEventsType,
    FastqSetStateChangeStatusEventsType
)
from ..models.fastq import FastqResponseDict
from ..models.fastq_set import FastqSetResponseDict


if typing.TYPE_CHECKING:
    from mypy_boto3_events import EventBridgeClient


def get_event_client() -> 'EventBridgeClient':
    """
    Get the event client for AWS EventBridge.
    """
    return boto3.client('events')


def put_event(
        event_detail_type: str,
        event_status: str,
        event_detail: Dict
):
    # DEBUG
    if environ.get(EVENT_BUS_NAME_ENV_VAR) == 'local':
        return
    get_event_client().put_events(
        Entries=[
            {
                'EventBusName': environ[EVENT_BUS_NAME_ENV_VAR],
                'Source': environ[EVENT_SOURCE_ENV_VAR],
                'DetailType': event_detail_type,
                'Detail': json.dumps(
                    dict(
                        status=event_status,
                        **event_detail,
                    ),
                ),
            },
        ]
    )

# Update events
def put_fastq_update_event(
        fastq_response_object: Union[FastqResponseDict, Dict],
        event_status: FastqStateChangeStatusEventsType
):
    """
    Put a update event to the event bus.
    """
    put_event(
        event_detail_type=environ[EVENT_DETAIL_TYPE_FASTQ_STATE_CHANGE_ENV_VAR],
        event_status=event_status,
        event_detail=fastq_response_object,
    )


def put_fastq_set_update_event(
        fastq_set_response_object: Union[FastqSetResponseDict, Dict],
        event_status: FastqSetStateChangeStatusEventsType
):
    """
    Put a update event to the event bus.
    """
    put_event(
        event_detail_type=environ[EVENT_DETAIL_TYPE_FASTQ_SET_STATE_CHANGE_ENV_VAR],
        event_status=event_status,
        event_detail=fastq_set_response_object
    )
