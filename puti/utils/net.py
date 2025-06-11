"""
@Author: obstacle
@Time: 15/01/25 17:58
@Description:  
"""
import traceback

from puti.logs import logger_factory

logger = logger_factory.default


def after_retry_callback(retry_state):
    if retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        if exception:
            logger.e(f"Retry attempt #{retry_state.attempt_number} failed with exception:")
            traceback.print_exception(type(exception), exception, exception.__traceback__)
    logger.e(f"Retried {retry_state.attempt_number} times.")
    logger.info(f"Retried {retry_state.attempt_number} times.")
