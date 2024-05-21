#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from typing import Any, Iterable, Mapping

from destination_amplitude.amplitude_client import AmplitudeClient

from airbyte_cdk import AirbyteLogger
from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status, Type


class DestinationAmplitude(Destination):
    def write(
        self, config: Mapping[str, Any], configured_catalog: ConfiguredAirbyteCatalog, input_messages: Iterable[AirbyteMessage]
    ) -> Iterable[AirbyteMessage]:

        list_events = []
        client = AmplitudeClient(config)
        for message in input_messages:
            if message.type == Type.STATE:
                yield message
            elif message.type == Type.RECORD:
                record = message.record
                event = client.create_event(record.data)
                list_events.append(event)
            else:
                continue
        client.send(list_events)

    def check(self, logger: AirbyteLogger, config: Mapping[str, Any]) -> AirbyteConnectionStatus:
        try:
            client = AmplitudeClient(config)._get_client()
            return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
