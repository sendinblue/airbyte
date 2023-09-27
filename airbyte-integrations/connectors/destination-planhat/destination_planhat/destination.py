#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from typing import Any, Iterable, Mapping

from airbyte_cdk import AirbyteLogger
from airbyte_cdk.destinations import Destination
from airbyte_cdk.models import AirbyteConnectionStatus, AirbyteMessage, ConfiguredAirbyteCatalog, Status, Type

from destination_planhat.client import PlanHatClient


class DestinationPlanhat(Destination):
    def write(
        self, config: Mapping[str, Any], configured_catalog: ConfiguredAirbyteCatalog, input_messages: Iterable[AirbyteMessage]
    ) -> Iterable[AirbyteMessage]:
        client = PlanHatClient(**config)

        http_method = client.http_method
        for message in input_messages:
            if message.type == Type.STATE:
                yield message
            elif message.type == Type.RECORD:
                record = message.record
                if http_method == "PUT":
                    client.queue_write_operation(record.data)
                else:
                    response = client.write(record.data)
                    client.print_error(response, "message")
            else:
                continue
        if (http_method == "PUT") and (len(client.write_buffer) != 0):
            client.flush()

    def check(self, logger: AirbyteLogger, config: Mapping[str, Any]) -> AirbyteConnectionStatus:
        try:
            client = PlanHatClient(**config)
            response = client.get_list()
            if response.status_code != 200:
                raise Exception("Invalid connection parameters.")
            else:
                return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"An exception occurred: {repr(e)}")
