#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_zendesk_support_custom import SourceZendeskSupportCustom

if __name__ == "__main__":
    source = SourceZendeskSupportCustom()
    launch(source, sys.argv[1:])
