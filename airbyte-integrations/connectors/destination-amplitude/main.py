#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


import sys

from destination_amplitude import DestinationAmplitude

if __name__ == "__main__":
    DestinationAmplitude().run(sys.argv[1:])
