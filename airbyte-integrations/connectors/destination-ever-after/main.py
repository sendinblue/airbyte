#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#


import sys

from destination_ever_after import DestinationEverAfter

if __name__ == "__main__":
    DestinationEverAfter().run(sys.argv[1:])
