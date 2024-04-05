#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

from abc import ABC
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Tuple

import pymongo
import ssl
from bson.timestamp import Timestamp
from bson import ObjectId

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

class JsonEncoder():
    def encode(self, o):
        def handle_object(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    obj[key] = handle_object(value)
            elif isinstance(obj, list):
                obj = [handle_object(item) for item in obj]
            elif isinstance(obj, ObjectId):
                return str(obj)
            return obj
        return handle_object(o)

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
            "username": config.get('user', None),
            "password": config.get('password', None),
            "authSource": config['authsource'],
            "ssl": use_ssl,
            "replicaset": config.get('replica_set', None),
            "readPreference": 'secondaryPreferred'
        }
        if config.get('port', None):
            connection_params["port"]= int(config["port"])

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
        cursor = collection.find({}).limit(10)  # Adjust the limit as necessary
        for doc in cursor:
            for key in doc.keys():
                # Set the type of each column as string without inspecting the value
                schema['properties'][key] = {'type': 'string'}
                schema['properties']["_collection_last_update"] = {'type': 'string'}
        return schema
    
    def read(self, logger, config, catalog, state):
        client = self.get_client(logger, config)
        db = client[config['database']]
        oplog = client['local']['oplog.rs']
         
        for configured_stream in catalog.streams:
            sync_mode = configured_stream.sync_mode
            stream = configured_stream.stream
            collection_name = stream.name
            collection = db[collection_name]
            query = {}

            if sync_mode == SyncMode.incremental:
                state_collection_last_update = None
                for state_message in state:
                    if state and state_message.stream.stream_descriptor.name == collection_name and state_message.stream.stream_state._collection_last_update:
                        state_collection_last_update = Timestamp(int(state_message.stream.stream_state._collection_last_update), 1)

                start_date = Timestamp(int(datetime.strptime(config['start_date'], "%Y-%m-%dT%H:%M:%S").timestamp()), 1) if config.get('start_date', None) else Timestamp(0,1) 

                filtre = {
                    'ts': {'$gt': max(state_collection_last_update, start_date) if state_collection_last_update else start_date},
                    'op': {'$in': ['i', 'u', 'd']},
                    'ns': f'{config["database"]}.{collection_name}'
                }
                pipeline = [
                    {"$match": filtre},
                    {"$sort": {"ts": -1}},  
                    {"$group": {
                        "_id": {
                            "$cond": {
                                "if": {"$eq": ["$op", "u"]},
                                "then": "$o2._id",
                                "else": "$o._id"
                            }
                        },
                        "recentDate": {"$first": "$ts"}
                    }},
                ]
                distinct_ids_cursor = oplog.aggregate(pipeline)
                distinct_ids_list = []
                recent_dates = []

                for id_obj in distinct_ids_cursor:
                    if id_obj["_id"] is not None:
                        distinct_ids_list.append(id_obj["_id"])
                        recent_dates.append(id_obj["recentDate"]) 
                logger.info(f"Sync objects for {collection_name} :{len(distinct_ids_list)}")

                query = {'_id': {'$in': distinct_ids_list}}
                _collection_last_update = max(recent_dates).time if recent_dates else None
    
            cursor = collection.find(query)
            
            for doc in cursor:
                doc['_collection_last_update'] = _collection_last_update
                doc = JsonEncoder().encode(doc)
                record = AirbyteRecordMessage(
                    stream=collection_name,
                    data=dict(),
                    emitted_at=int(datetime.now().timestamp()) * 1000,
                )
                yield AirbyteMessage(type=Type.RECORD, record=record)

            if sync_mode == SyncMode.incremental:
                stream_state = AirbyteStateMessage(
                    type=AirbyteStateType.STREAM,
                    stream=AirbyteStreamState(
                        stream_descriptor=StreamDescriptor(name=collection_name),
                        stream_state=AirbyteStateBlob.parse_obj({"_collection_last_update": _collection_last_update}),
                    ),
                )
                yield AirbyteMessage(type=Type.STATE, state=stream_state)

        client.close()


