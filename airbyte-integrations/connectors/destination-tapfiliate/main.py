#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


import sys

from destination_tapfiliate import DestinationTapfiliate

if __name__ == "__main__":
    DestinationTapfiliate().run(sys.argv[1:])
