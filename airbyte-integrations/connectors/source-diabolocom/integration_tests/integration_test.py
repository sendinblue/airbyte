#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


import requests
import pytest
import json

API_ENDPOINT = "https://public-fr6.engage.diabolocom.com/api/v1/account/users"
CONFIG_FILE_PATH = "secrets/config.json"


@pytest.fixture(scope="session", autouse=True)
def connector_setup():
    """This fixture is a placeholder for external resources that acceptance test might require."""
    # TODO: setup test dependencies if needed. otherwise remove the TODO comments
    yield
    # TODO: clean up test dependencies


# Helper function to read API key from the configuration file
def get_api_key():
    with open(CONFIG_FILE_PATH, "r") as config_file:
        config_data = json.load(config_file)
        return config_data.get("api_key", "")


# Acceptance test to retrieve the user stream from the API
def test_stream_success():
    # Get the API key from the configuration file
    api_key = get_api_key()
    print(api_key)

    # Set up headers with the API key
    headers = {
        "Private-Token": api_key,
    }
    # Make a GET request to the API endpoint
    response = requests.get(API_ENDPOINT, headers=headers)

    # Check if the request was successful (status code 200)
    assert response.status_code == 200


def test_stream_error():
    invalid_api_key = "invalid_api_key"

    headers = {
        "Private-Token": invalid_api_key,
    }

    # Make a GET request to the API endpoint
    response = requests.get(API_ENDPOINT, headers=headers)

    assert response.status_code == 401


# Test for handling invalid endpoints (404 Not Found)
def test_invalid_endpoint():
    api_key = get_api_key()

    headers = {
        "Private-Token": api_key,
    }

    # Make a GET request to an invalid API endpoint
    response = requests.get(f"{API_ENDPOINT}/invalid", headers=headers)

    assert response.status_code == 400
