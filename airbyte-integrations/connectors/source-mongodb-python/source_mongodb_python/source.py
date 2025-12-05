#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

from abc import ABC
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Tuple
import re

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
    AirbyteStateType,
)


class JsonEncoder:
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
            client.admin.command("ping")
            logger.info("Successfully connected to MongoDB.")
            return AirbyteConnectionStatus(status=Status.SUCCEEDED)
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            return AirbyteConnectionStatus(status=Status.FAILED, message=f"Config Check - An exception occurred: {str(e)}")

    def get_client(self, logger, config: Mapping[str, Any]) -> Tuple[bool, Optional[Any]]:
        """
        Attempts to connect to MongoDB using the provided configuration.

        :param logger: Airbyte logger to output logs from this method.
        :param config: A mapping containing the user-provided configuration as specified by the source's spec.yaml
        :return: A tuple of (bool, optional error message). True indicates a successful connection check.
        """
        # Attempt connection using individual parameters
        verify_mode = config.get("verify_mode", "true") == "true"
        use_ssl = config.get("ssl", "false") == "true"

        connection_params = {
            "host": config["host"],
            "username": config.get("user", None),
            "password": config.get("password", None),
            "authSource": config["authsource"],
            "ssl": use_ssl,
            "replicaset": config.get("replica_set", None),
            "readPreference": "secondaryPreferred",
        }
        if config.get("port", None):
            connection_params["port"] = int(config["port"])

        if not verify_mode and use_ssl:
            connection_params["ssl_cert_reqs"] = ssl.CERT_NONE

        client = pymongo.MongoClient(**connection_params)
        client.admin.command("ping")

        return client

    def discover(self, logger, config):
        client = self.get_client(logger, config)
        db = client[config["database"]]
        streams = []
        for collection_name in db.list_collection_names():
            stream = AirbyteStream(
                name=collection_name,
                json_schema=self._get_json_schema_for_collection(db[collection_name], config),
                supported_sync_modes=["full_refresh", "incremental"],
            )
            streams.append(stream)
        return AirbyteCatalog(streams=streams)

    def _get_json_schema_for_collection(self, collection, config):
        if config.get("schemaless"):
            schema = {"properties": {"data": {"type": "object"}}}
        else:
            schema = {"properties": {}}
            cursor = collection.find({}).limit(10)
            for doc in cursor:
                for key in doc.keys():
                    schema["properties"][key] = {"type": "string"}
        schema["properties"]["_sdc_deleted_at"] = {"type": "string"}
        return schema

    def _get_incremental_cursor_field(self, configured_stream):
        """Get the cursor field for incremental sync without oplog based on stream configuration."""
        if hasattr(configured_stream, 'cursor_field') and configured_stream.cursor_field:
            cursor_field = configured_stream.cursor_field[0] if isinstance(configured_stream.cursor_field, list) else configured_stream.cursor_field
            # Log which cursor field is being used
            return cursor_field
        
        # Default fallback - try to find a better field than _id
        return "updated_at"

    def _parse_cursor_value(self, cursor_value, cursor_field):
        """Parse cursor value based on field type."""
        if cursor_field == "_id":
            return ObjectId(cursor_value) if isinstance(cursor_value, str) else cursor_value
        elif isinstance(cursor_value, str):
            try:
                # Try to parse as datetime
                return datetime.strptime(cursor_value, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                try:
                    return datetime.strptime(cursor_value, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    return cursor_value
        return cursor_value

    def read(self, logger, config, catalog, state):
        client = self.get_client(logger, config)
        db = client[config["database"]]
        
        has_replica_set = config.get("replica_set") is not None
        oplog = client["local"]["oplog.rs"] if has_replica_set else None

        for configured_stream in catalog.streams:
            sync_mode = configured_stream.sync_mode
            stream = configured_stream.stream
            collection_name = stream.name
            collection = db[collection_name]
            _collection_last_update = Timestamp(int(datetime.now().timestamp()), 0)
            state_collection_last_update = Timestamp(0, 0)
            for state_message in state:
                if (
                    state_message.stream.stream_descriptor.name == collection_name
                    and state_message.stream.stream_state._collection_last_update
                ):
                    timestamp_value, increment = map(int, re.findall(r"\d+", state_message.stream.stream_state._collection_last_update))
                    state_collection_last_update = Timestamp(timestamp_value, increment)

            query = {}

            if sync_mode == SyncMode.incremental and has_replica_set and state_collection_last_update > Timestamp(0, 0):
                # Oplog-based incremental sync (replica set required)
                start_date = (
                    Timestamp(int(datetime.strptime(config["start_date"], "%Y-%m-%dT%H:%M:%S").timestamp()), 0)
                    if config.get("start_date", None)
                    else Timestamp(0, 0)
                )

                filtre = {
                    "ts": {"$gt": max(state_collection_last_update, start_date) if state_collection_last_update else start_date},
                    "op": {"$in": ["i", "u", "d"]},
                    "ns": f'{config["database"]}.{collection_name}',
                }
                cursor_pipeline = [{"$match": filtre}]

                ids_cursor = oplog.aggregate(cursor_pipeline)

                deletes_to_process = []
                ids_list = []
                recent_dates = []

                for id_obj in ids_cursor:
                    if id_obj["op"] == "d":
                        deletes_to_process.append(
                            {
                                "_id": str(id_obj["o"]["_id"]),
                                "_sdc_deleted_at": datetime.utcfromtimestamp(id_obj["ts"].time).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                            }
                        )
                        recent_dates.append(id_obj["ts"])
                    elif id_obj["op"] == "i":
                        ids_list.append(id_obj["o"]["_id"])
                        recent_dates.append(id_obj["ts"])
                    elif id_obj["op"] == "u":
                        ids_list.append(id_obj["o2"]["_id"])
                        recent_dates.append(id_obj["ts"])

                ids_list = list(set(ids_list))
                logger.info(f"Sync objects for '{collection_name}' :{len(ids_list)} with deletes: {len(deletes_to_process)}")
                _collection_last_update = max(recent_dates) if recent_dates else _collection_last_update

                for delete_doc in deletes_to_process:
                    if config.get("schemaless"):
                        _sdc_deleted_at = delete_doc.pop("_sdc_deleted_at")
                        delete_doc = {"data": delete_doc, "_sdc_deleted_at": _sdc_deleted_at}
                    delete_doc["_collection_last_update"] = str(_collection_last_update)
                    record = AirbyteRecordMessage(
                        stream=collection_name,
                        data=delete_doc,
                        emitted_at=int(datetime.now().timestamp()) * 1000,
                    )
                    yield AirbyteMessage(type=Type.RECORD, record=record)

                BATCH_SIZE = 10000
                for i in range(0, len(ids_list), BATCH_SIZE):
                    batch_limit = i + BATCH_SIZE
                    logger.info(f"BATCH stream {i} : {batch_limit}")
                    query = {"_id": {"$in": ids_list[i:batch_limit]}}
                    cursor = collection.find(query)
                    for doc in cursor:
                        doc = JsonEncoder().encode(doc)
                        if config.get("schemaless"):
                            doc = {"data": doc}
                        doc["_collection_last_update"] = str(_collection_last_update)
                        record = AirbyteRecordMessage(
                            stream=collection_name,
                            data=doc,
                            emitted_at=int(datetime.now().timestamp()) * 1000,
                        )
                        yield AirbyteMessage(type=Type.RECORD, record=record)
                    logger.info(
                        f"{len(ids_list[i : i + BATCH_SIZE ])} out of {len(ids_list)} record retreived from '{collection_name}' stream"
                    )

            elif sync_mode == SyncMode.incremental and not has_replica_set:
                cursor_field = self._get_incremental_cursor_field(configured_stream)
                last_cursor_value = None
                
                for state_message in state:
                    if state_message.stream.stream_descriptor.name == collection_name:
                        state_data = state_message.stream.stream_state
                        if hasattr(state_data, cursor_field):
                            last_cursor_value = getattr(state_data, cursor_field)
                        elif hasattr(state_data, '__dict__') and cursor_field in state_data.__dict__:
                            last_cursor_value = state_data.__dict__[cursor_field]
                        break
                
                if last_cursor_value:
                    parsed_cursor = self._parse_cursor_value(last_cursor_value, cursor_field)
                    query[cursor_field] = {"$gt": parsed_cursor}
                elif config.get("start_date"):
                    if cursor_field == "_id":
                        start_timestamp = int(datetime.strptime(config["start_date"], "%Y-%m-%dT%H:%M:%S").timestamp())
                        start_objectid = ObjectId.from_datetime(datetime.fromtimestamp(start_timestamp))
                        query[cursor_field] = {"$gt": start_objectid}
                    else:
                        query[cursor_field] = {"$gt": datetime.strptime(config["start_date"], "%Y-%m-%dT%H:%M:%S")}
                
                logger.info(f"Incremental sync for '{collection_name}' using cursor field '{cursor_field}' with query: {query}")
                
                cursor = collection.find(query).sort(cursor_field, 1)
                max_cursor_value = None
                
                for doc in cursor:
                    doc = JsonEncoder().encode(doc)
                    if config.get("schemaless"):
                        doc = {"data": doc}
                    
                    cursor_value = doc.get(cursor_field) if not config.get("schemaless") else doc["data"].get(cursor_field)
                    if cursor_value:
                        if cursor_field == "_id":
                            cursor_value = str(cursor_value)
                        elif isinstance(cursor_value, datetime):
                            cursor_value = cursor_value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                        max_cursor_value = cursor_value
                    
                    record = AirbyteRecordMessage(
                        stream=collection_name,
                        data=doc,
                        emitted_at=int(datetime.now().timestamp()) * 1000,
                    )
                    yield AirbyteMessage(type=Type.RECORD, record=record)
                
                if max_cursor_value and sync_mode == SyncMode.incremental:
                    stream_state = AirbyteStateMessage(
                        type=AirbyteStateType.STREAM,
                        stream=AirbyteStreamState(
                            stream_descriptor=StreamDescriptor(name=collection_name),
                            stream_state=AirbyteStateBlob.parse_obj({
                                cursor_field: max_cursor_value
                            }),
                        ),
                    )
                    yield AirbyteMessage(type=Type.STATE, state=stream_state)
                
                continue 

            else:

                cursor = collection.find(query)
                for doc in cursor:
                    doc = JsonEncoder().encode(doc)
                    if config.get("schemaless"):
                        doc = {"data": doc}
                    doc["_collection_last_update"] = str(_collection_last_update)
                    record = AirbyteRecordMessage(
                        stream=collection_name,
                        data=doc,
                        emitted_at=int(datetime.now().timestamp()) * 1000,
                    )
                    yield AirbyteMessage(type=Type.RECORD, record=record)

            if sync_mode == SyncMode.incremental:
                stream_state = AirbyteStateMessage(
                    type=AirbyteStateType.STREAM,
                    stream=AirbyteStreamState(
                        stream_descriptor=StreamDescriptor(name=collection_name),
                        stream_state=AirbyteStateBlob.parse_obj({"_collection_last_update": str(_collection_last_update)}),
                    ),
                )
                yield AirbyteMessage(type=Type.STATE, state=stream_state)

        client.close()
