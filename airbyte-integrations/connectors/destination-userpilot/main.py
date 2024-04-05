#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


import sys

from destination_userpilot import DestinationUserpilot

if __name__ == "__main__":
    DestinationUserpilot().run(sys.argv[1:])
