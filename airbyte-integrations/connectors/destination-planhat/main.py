#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#


import sys

from destination_planhat import DestinationPlanhat

if __name__ == "__main__":
    DestinationPlanhat().run(sys.argv[1:])
