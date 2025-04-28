#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

import logging

from typing import Any, Iterable, Mapping

from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status

from destination_partnerstack.client import PartnerStackClient


class DestinationPartnerstack(Destination):
    def write(
        self, config: Mapping[str, Any], configured_catalog: ConfiguredAirbyteCatalog, input_messages: Iterable[AirbyteMessage]
    ) -> Iterable[AirbyteMessage]:
        client = PartnerStackClient(**config)
        for message in input_messages:
            if message.type == Type.STATE:
                yield message
            elif message.type == Type.RECORD:
                data = message.record.data
                if client.method == 'PATCH':
                    if client.key not in data:
                        raise Exception(f"{client.key} not found in record: {data}")
                    else:
                        response = client.update(client.key, data)
                else:
                    response = client.write(data)
                if response.status_code != 200:
                    logger.error({"record": message.record.data, "error": response.json()})
            else:
                continue

    def check(self, logger: logging.Logger, config: Mapping[str, Any]) -> AirbyteConnectionStatus:
        try:
            client = PartnerStackClient(**config)
            response = client.list()
            if response.status_code != 200:
                raise Exception("Invalid connection parameters.")
            else:
                return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
