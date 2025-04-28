#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#


import sys

from destination_partnerstack import DestinationPartnerstack

if __name__ == "__main__":
    DestinationPartnerstack().run(sys.argv[1:])
