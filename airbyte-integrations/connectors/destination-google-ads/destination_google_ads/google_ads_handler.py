# Copyright (c) 2024 Airbyte, Inc., all rights reserved.

from typing import Mapping

from destination_google_ads.error_handler import print_results
from destination_google_ads.google_ads_offline_conversion import click_conversions
from google.ads.googleads.client import GoogleAdsClient


class GoogleAdsHandler:
    def __init__(self, config):
        self.developer_token = config["developer_token"]
        self.oauth_client_id = config["oauth_client_id"]
        self.oauth_client_secret = config["oauth_client_secret"]
        self.refresh_token = config["refresh_token"]
        self.customer_id = config["customer_id"]
        self.offline_conversion = config["offline_conversion"].replace(" ", "_").lower()
        self.api_version = "v15"

        self.batch_size = 500
        self.write_batch = []
        self.client = self.__get_client()

    def __get_client(self):
        """
        Get google ads client
        """

        CONFIG = {
            "use_proto_plus": True,
            "developer_token": self.developer_token,
            "client_id": self.oauth_client_id,
            "client_secret": self.oauth_client_secret,
            "refresh_token": self.refresh_token,
            # "validate_only": True,
        }

        client = GoogleAdsClient.load_from_dict(config_dict=CONFIG, version=self.api_version)

        return client

    def get_customers(self):
        customer_service = self.client.get_service("CustomerService")
        accessible_customers = customer_service.list_accessible_customers()
        return accessible_customers.resource_names

    def queue_batch(self, data: Mapping):
        if "conversion_id" not in data:
            raise Exception(f"Need a Conversion Id to upload conversion data")
        else:
            record = click_conversions(self.client, data, self.customer_id, data["conversion_id"])

        self.write_batch.append(record)
        if len(self.write_batch) == self.batch_size:
            self.flush()

    def flush(self):
        self.send_data(self.write_batch)
        self.write_batch.clear()

    def send_data(self, data: list) -> None:
        """
        Send data to google ads API
        :param data: List of click conversions
        :return: conversion response
        """
        conversion_upload_service = self.client.get_service("ConversionUploadService")
        request = self.client.get_type("UploadClickConversionsRequest")
        request.customer_id = self.customer_id
        request.conversions.extend(data)
        request.partial_failure = True
        conversion_upload_response = conversion_upload_service.upload_click_conversions(
            request=request,
        )
        print_results(self.client, conversion_upload_response)
