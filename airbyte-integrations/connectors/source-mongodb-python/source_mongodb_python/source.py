#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

from abc import ABC
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Tuple

import pymongo
import ssl

from airbyte_cdk.sources.source import Source
from airbyte_cdk.models import (
    AirbyteCatalog,
    AirbyteRecordMessage,
    AirbyteConnectionStatus,
    AirbyteStream,
    Status,
    SyncMode,
    Type,
    AirbyteMessage,
    AirbyteStateMessage,
    StreamDescriptor,
    AirbyteStateBlob,
    AirbyteStreamState,
    AirbyteStateType
)

class SourceMongodbPython(Source):
    
    def check(self, logger, config: Mapping[str, Any]) -> Tuple[bool, Optional[Any]]:
        try:
            client = self.get_client(logger, config)
            client.admin.command('ping')
            logger.info('Successfully connected to MongoDB.')
            return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            return AirbyteConnectionStatus(
                status=Status.FAILED, message=f"Config Check - An exception occurred: {str(e)}"
            )
    
    def get_client(self, logger, config: Mapping[str, Any]) -> Tuple[bool, Optional[Any]]:
        """
        Attempts to connect to MongoDB using the provided configuration.
        
        :param logger: Airbyte logger to output logs from this method.
        :param config: A mapping containing the user-provided configuration as specified by the source's spec.yaml
        :return: A tuple of (bool, optional error message). True indicates a successful connection check.
        """
        # Attempt connection using individual parameters
        verify_mode = config.get('verify_mode', 'true') == 'true'
        use_ssl = config.get('ssl', 'false') == 'true'

        connection_params = {
            "host": config['host'],
            "port": int(config['port']),
            "username": config.get('user', None),
            "password": config.get('password', None),
            "authSource": config['database'],
            "ssl": use_ssl,
            "replicaset": config.get('replica_set', None),
            "readPreference": 'secondaryPreferred'
        }

        if not verify_mode and use_ssl:
            connection_params["ssl_cert_reqs"] = ssl.CERT_NONE

        client = pymongo.MongoClient(**connection_params)
        client.admin.command('ping')

        return client

    def discover(self, logger, config):

        client = self.get_client(logger, config)
        db = client[config['database']]
        streams = []
        for collection_name in db.list_collection_names():
            stream = AirbyteStream(
                name=collection_name,
                json_schema=self._get_json_schema_for_collection(db[collection_name]),
                supported_sync_modes=["full_refresh", "incremental"],
            )
            streams.append(stream)
        return AirbyteCatalog(streams=streams)

    def _get_json_schema_for_collection(self, collection):
        schema = {'properties': {}}

        # Iterate over the documents in the collection to gather schema information
        cursor = collection.find({})
        for doc in cursor:
            for key, value in doc.items():
                # Always set the type of each column as string
                schema['properties'][key] = {'type': 'string'}

        return schema

    def _transform_state(self,state):
        # New dictionary to store the transformed data
        transformed_state = {}

        # Loop through each item in the original list
        for item in state:
            # Extract the collection name and run datetime
            collection_name = item["streamDescriptor"]["name"]
            run_datetime = item["streamState"]["last_run"]
            
            # Add to the new dictionary
            transformed_state[collection_name] = run_datetime
        
        return transformed_state

    def read(self, logger, config, catalog, state):
        client = self.get_client(logger, config)
        db = client[config['database']]


        # transformed_state = self._transform_state(state)

        for configured_stream in catalog.streams:
            stream = configured_stream.stream
            collection_name = stream.name
            last_run = None
            for state__message in state:
                if state__message.stream.stream_descriptor.name == collection_name:
                    last_run = state__message.stream.stream_state.last_run
           
            logger.info("SSSTATE")
            logger.info(last_run)
            logger.info("SSSTATE")
            collection = db[collection_name]

            sync_mode = configured_stream.sync_mode
            query = {}

            # Find the corresponding state for the current collection, if it exists
            if sync_mode == SyncMode.incremental:
                state_value = last_run
                if state_value is not None:
                    query["$and"] = [
                        {"updated_at": {"$gt": state_value}}
                    ]
                if config.get('start_date'):
                    start_date_query = {"updated_at": {"$gt": config['start_date']}}
                    if "$and" in query:
                        query["$and"].append(start_date_query)
                    else:
                        query["$and"] = [start_date_query]


            cursor = collection.find(query)
            run_datetime = datetime.now()

            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                record = AirbyteRecordMessage(
                    stream=collection_name,
                    data=doc,
                    emitted_at=int(run_datetime.timestamp()) * 1000,
                )
                yield AirbyteMessage(type=Type.RECORD, record=record)

            if sync_mode == SyncMode.incremental:
                stream_state = AirbyteStateMessage(
                type=AirbyteStateType.STREAM,
                stream=AirbyteStreamState(
                    stream_descriptor=StreamDescriptor(name=collection_name),
                    stream_state=AirbyteStateBlob.parse_obj({"last_run": run_datetime}),
                ),
                )
                yield AirbyteMessage(type=Type.STATE, state=stream_state)
        client.close()

