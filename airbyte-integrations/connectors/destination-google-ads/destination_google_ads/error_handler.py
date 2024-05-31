from logging import getLogger

LOGGER = getLogger("airbyte")


def _print_google_ads_failures(client, status):
    """Prints the details for partial failure errors and warnings.

    Both partial failure errors and warnings are returned as Status instances,
    which include serialized GoogleAdsFailure objects. Here we deserialize
    each GoogleAdsFailure and print the error details it includes.

    Args:
        client: An initialized Google Ads API client.
        status: a google.rpc.Status instance.
    """
    for detail in status.details:
        google_ads_failure = client.get_type("GoogleAdsFailure")
        # Retrieve the class definition of the GoogleAdsFailure instance
        # with type() in order to use the "deserialize" class method to parse
        # the detail string into a protobuf message instance.
        failure_instance = type(google_ads_failure).deserialize(detail.value)
        for error in failure_instance.errors:
            LOGGER.warning(
                "A partial failure or warning at index "
                f"{error.location.field_path_elements[0].index} occurred.\n"
                f"Message: {error.message}\n"
                f"Code: {error.error_code}"
            )


def print_results(client, response):
    # Check for existence of any partial failures in the response.
    partial_failure = getattr(response, "partial_failure_error", None)
    code = getattr(partial_failure, "code", None)
    if code != 0:
        _print_google_ads_failures(client, response.partial_failure_error)
    else:
        LOGGER.info(
            "All operations completed successfully. No partial failure to show."
        )