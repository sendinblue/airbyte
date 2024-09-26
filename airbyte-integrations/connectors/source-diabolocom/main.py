#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_diabolocom import SourceDiabolocom

if __name__ == "__main__":
    source = SourceDiabolocom()
    launch(source, sys.argv[1:])
