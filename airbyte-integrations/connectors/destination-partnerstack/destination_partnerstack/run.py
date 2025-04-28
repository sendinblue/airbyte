#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from .destination import DestinationPartnerstack

def run():
    destination = DestinationPartnerstack()
    destination.run(sys.argv[1:])
