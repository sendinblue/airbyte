import unittest
from unittest.mock import patch, MagicMock
from bson.timestamp import Timestamp

from airbyte_cdk.models import SyncMode, AirbyteStream, Type, AirbyteMessage, ConfiguredAirbyteStream, ConfiguredAirbyteCatalog
from source_mongodb_python.source import SourceMongodbPython


class TestSourceMongodbPython(unittest.TestCase):

    def test_read_full_refresh(self):
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_oplog = MagicMock()

        # Set up the mock behavior
        mock_client.__getitem__.side_effect = lambda name: mock_db if name == "test_db" else mock_oplog if name == "local" else None
        mock_db.__getitem__.return_value = mock_collection
        mock_oplog.__getitem__.return_value = MagicMock()
        mock_oplog.__getitem__.return_value.aggregate.return_value = []

        mock_collection.find.return_value = [{"_id": "123", "data": "value"}]

        stream = ConfiguredAirbyteStream(
            stream=AirbyteStream.model_validate({"name": "test_collection", "json_schema": {}, "supported_sync_modes": ["full_refresh"]}),
            sync_mode="full_refresh",
            destination_sync_mode="overwrite",
        )

        catalog = ConfiguredAirbyteCatalog(streams=[stream])

        state = []

        source = SourceMongodbPython()
        logger = MagicMock()
        config = {"database": "test_db", "schemaless": False}

        source.get_client = MagicMock(return_value=mock_client)

        result = list(source.read(logger, config, catalog, state))

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], AirbyteMessage)
        self.assertEqual(result[0].type, Type.RECORD)
        self.assertEqual(result[0].record.stream, "test_collection")
        self.assertIn("_id", result[0].record.data)
        self.assertEqual(result[0].record.data["_id"], "123")


if __name__ == "__main__":
    unittest.main()


# poetry run python -m unittest unit_tests/test_read_oplog.py
