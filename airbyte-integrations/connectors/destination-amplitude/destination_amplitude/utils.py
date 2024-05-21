from logging import Logger, getLogger
from datetime import datetime

logger = getLogger("airbyte")


def callback_function(event, code, message=None) -> None:
    """
    A callback function
    :param event: the event that triggered this callback
    :param code: status code of request response
    :param message: a optional string message for more detailed information
    :return: None
    """
    now = datetime.strftime("%Y-%m-%d %H:%M:%S")
    logger.info(
        "upload time {}\n event {}\n response code: {}\n response message: {}".format(
            now, event, code, message
        )
    )