#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

import logging
from datetime import datetime

from airbyte_cdk.sources.file_based.remote_file import RemoteFile
from airbyte_cdk.sources.file_based.stream.cursor import DefaultFileBasedCursor


class Cursor(DefaultFileBasedCursor):
    @staticmethod
    def get_file_uri(file: RemoteFile) -> str:
        return file.uri.split("?")[0]

    def add_file(self, file: RemoteFile) -> None:
        uri = self.get_file_uri(file)
        self._file_to_datetime_history[uri] = file.last_modified.strftime(self.DATE_TIME_FORMAT)
        if len(self._file_to_datetime_history) > 1:
            # Get the earliest file based on its last modified date and its uri
            oldest_file = self._compute_earliest_file_in_history()
            if oldest_file:
                del self._file_to_datetime_history[oldest_file.uri]
            else:
                raise Exception(
                    "The history is full but there is no files in the history. This should never happen and might be indicative of a bug in the CDK."
                )

    def _should_sync_file(self, file: RemoteFile, logger: logging.Logger) -> bool:

        if file.last_modified > max(self.get_start_time(), datetime.fromisoformat(self.get_state().get("_ab_source_file_last_modified").split('Z')[0])) if self.get_state().get("_ab_source_file_last_modified") is not None else self.get_start_time(): 
            return True
        else:
            return False
      