#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from .source import SourceMongodbPython


def run():
    source = SourceMongodbPython()
    launch(source, sys.argv[1:])
