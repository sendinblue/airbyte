#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

import logging
from typing import Any, Iterable, Mapping

from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status, Type
from destination_webhook.client import WebhookClient

class DestinationWebhook(Destination):
    def write(
        self, config: Mapping[str, Any], configured_catalog: ConfiguredAirbyteCatalog, input_messages: Iterable[AirbyteMessage]
    ) -> Iterable[AirbyteMessage]:

        client = WebhookClient(**config)

        for message in input_messages:
            if message.type == Type.STATE:
                yield message
            elif message.type == Type.RECORD:
                record = message.record
                client.queue_write_operation(record.data)
            else:
                continue
        if len(client.write_buffer) != 0:
            client.write(client.write_buffer)

    def check(self, logger: logging.Logger, config: Mapping[str, Any]) -> AirbyteConnectionStatus:
        try:
            client = WebhookClient(**config)
            response = client.check_url()
            if response.status_code == 200:
                return AirbyteConnectionStatus(status=Status.SUCCEEDED)
            else:
                return AirbyteConnectionStatus(status=Status.FAILED, message=f"Failed to connect to {config['url']}")
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
