#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

import contextlib
import csv
import errno
import json
import os
import datetime
from typing import Dict, List, TextIO, Optional

import paramiko
import smart_open


@contextlib.contextmanager
def sftp_client(
    host: str,
    port: int,
    username: str,
    password: str,
) -> paramiko.SFTPClient:
    with paramiko.SSHClient() as client:
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            host,
            port,
            username=username,
            password=password,
            look_for_keys=False,
        )
        sftp = client.open_sftp()
        yield sftp


class SftpClient:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        destination_path: str,
        port: int = 22,
        output_format: str = "json",
        file_prefix: str = "",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.destination_path = destination_path
        self.output_format = output_format.lower()
        self.file_prefix = file_prefix
        self._files: Dict[str, TextIO] = {}
        self._csv_headers: Dict[str, List[str]] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _get_path(self, stream: str) -> str:
        prefix = stream
        if self.file_prefix != "":
            prefix = f"{self.file_prefix}_{self.output_format}_{stream}"
        if self.output_format == "csv":
            return f"{self.destination_path}/{prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:  # default to json
            return f"{self.destination_path}/{prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    def _get_uri(self, stream: str) -> str:
        path = self._get_path(stream)
        return f"sftp://{self.username}:{self.password}@{self.host}:{self.port}/{path}"

    def _open(self, stream: str) -> TextIO:
        uri = self._get_uri(stream)
        return smart_open.open(uri, mode="a+")

    def close(self):
        for file in self._files.values():
            file.close()

    def write(self, stream: str, record: Dict) -> None:
        # Open the file if it's not already open
        if stream not in self._files:
            self._files[stream] = self._open(stream)
            s
        if self.output_format == "csv":
            # For CSV, we need to handle headers
            if stream not in self._csv_headers:
                # Get all fields from the first record
                headers = list(record.keys())
                self._csv_headers[stream] = headers
                
                # Write headers if file is empty (at position 0)
                file_pos = self._files[stream].tell()
                if file_pos == 0:
                    # Write headers directly to the file
                    header_text = ",".join(headers)
                    self._files[stream].write(f"{header_text}\n")
                    
            # Convert record to CSV line
            values = [str(record.get(field, "")) for field in self._csv_headers[stream]]
            text = ",".join(values)
            # Write directly to the file
            self._files[stream].write(f"{text}\n")
        else:  # default to json
            # For JSON, just write the record as a JSON line
            text = json.dumps(record)
            self._files[stream].write(f"{text}\n")

    def read_data(self, stream: str) -> List[Dict]:
        with self._open(stream) as file:
            pos = file.tell()
            file.seek(0)
            
            if self.output_format == "csv":
                reader = csv.DictReader(file)
                data = list(reader)
            else:  # default to json
                lines = file.readlines()
                data = [json.loads(line.strip()) for line in lines]
                
            file.seek(pos)
        return data

    def delete(self, stream: str) -> None:
        with sftp_client(self.host, self.port, self.username, self.password) as sftp:
            try:
                path = self._get_path(stream)
                sftp.remove(path)
            except IOError as err:
                # Ignore the case where the file doesn't exist, only raise the
                # exception if it's something else
                if err.errno != errno.ENOENT:
                    raise
