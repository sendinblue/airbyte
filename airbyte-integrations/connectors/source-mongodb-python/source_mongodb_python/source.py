#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

from abc import ABC
from datetime import datetime
from typing import Any, Generator, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import pymongo
import ssl

from airbyte_cdk.sources.source import Source
from airbyte_cdk.models import (
    AirbyteCatalog,
    AirbyteConnectionStatus,
    AirbyteMessage,
    AirbyteRecordMessage,
    AirbyteStream,
    ConfiguredAirbyteCatalog,
    Status,
    Type,
    SyncMode
)
from pymongo import MongoClient

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
            # Attempt connection using a DNS string
        if 'connection_uri' in config:
            parsed_uri = pymongo.uri_parser.parse_uri(config['connection_uri'])
            additional_config = {
                "username": parsed_uri['username'],
                "password": parsed_uri['password'],
                "authSource": parsed_uri['options']['authsource'],
                "user": parsed_uri['username'],
                "database": parsed_uri.get('database', 'admin')
            }

            if additional_config["user"] is None:
                logger.info("Set default user as admin")
                additional_config["user"] = "admin"

            config.update(additional_config)
            client = pymongo.MongoClient(config['connection_uri'])
            # Test the connection
            client.admin.command('ping')
            return client

        else:
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
        schema = {
        'properties': {
            '_id': {'type': 'string'}
        }}
        return schema


    def read(self, logger, config, catalog, state=None):
        client = self.get_client(logger, config)
        db = client[config['database']]

        for configured_stream in catalog.streams:
            stream = configured_stream.stream
            collection_name = stream.name  # Accès correct au nom du stream
            collection = db[collection_name]

            sync_mode = configured_stream.sync_mode
            query = {}
            if sync_mode == SyncMode.incremental and state and state.get(collection_name):
                state_value = state[collection_name]
                query = {"updated_at": {"$gt": state_value}}
            
            cursor = collection.find(query)
            for doc in cursor:
                print("----------")
                print(int(datetime.now().timestamp()) * 1000)
                print("----------")
                # record= AirbyteRecordMessage(stream=collection_name, data={"f1": "v1", "f2": "v2"}, emitted_at=111, type='e')
                record = AirbyteRecordMessage(
                    stream=collection_name,
                    data=doc,
                    emitted_at=int(datetime.now().timestamp()) * 1000,
                    type="3"
                )
                yield record

                # if sync_mode == SyncMode.incremental:
                #     updated_at = doc.get("updated_at")
                #     if updated_at:
                #         state[collection_name] = updated_at

        client.close()


#   def read(self, logger, config, catalog, state=None):
#         client = self.get_client(logger, config)
#         db = client[config['database']]

#         for configured_stream in catalog.streams:
#             stream = configured_stream.stream
#             collection_name = stream.name  # Accès correct au nom du stream
#             collection = db[collection_name]

#             # La logique ici est la même que l'exemple précédent
#             sync_mode = configured_stream.sync_mode
#             query = {}
#             if sync_mode == SyncMode.incremental and state and state.get(collection_name):
#                 state_value = state[collection_name]
#                 query = {"updated_at": {"$gt": state_value}}
            
#             cursor = collection.find(query)
#             for doc in cursor:
#                 record = AirbyteRecordMessage(
#                     stream=collection_name,
#                     data=doc,
#                     emitted_at=int(datetime.now().timestamp()) * 1000
#                 )
#                 yield record

#                 if sync_mode == SyncMode.incremental:
#                     updated_at = doc.get("updated_at")
#                     if updated_at:
#                         state[collection_name] = updated_at

#         client.close()
