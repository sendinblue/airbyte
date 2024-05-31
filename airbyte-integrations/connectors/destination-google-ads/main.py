#
# Copyright (c) 2024 Airbyte, Inc., all rights reserved.
#


import sys

from destination_google_ads import DestinationGoogleAds

if __name__ == "__main__":
    DestinationGoogleAds().run(sys.argv[1:])
