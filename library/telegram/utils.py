import logging
import traceback
from contextlib import asynccontextmanager
from typing import Optional

from izihawa_loglib import error_log
from telethon import errors, events


@asynccontextmanager
async def safe_execution(
    error_log=error_log,
    on_fail: Optional = None,
    level=logging.WARNING,
    is_logging_enabled: bool = True
):
    try:
        try:
            yield
        except events.StopPropagation:
            raise
        except errors.MessageNotModifiedError:
            pass
        except (
            errors.UserIsBlockedError,
            errors.QueryIdInvalidError,
            errors.MessageDeleteForbiddenError,
            errors.MessageIdInvalidError,
            errors.ChatAdminRequiredError,
        ) as e:
            if is_logging_enabled:
                error_log(e, level=level)
                traceback.print_exc()
        except ValueError as e:
            if e.args and e.args[0].startswith('Request was unsuccessful'):
                if is_logging_enabled:
                    error_log(e, level=level)
            else:
                raise
        except Exception as e:
            if is_logging_enabled:
                error_log(e, level=level)
                traceback.print_exc()
            if on_fail:
                await on_fail()
    except events.StopPropagation:
        raise
    except Exception as e:
        if is_logging_enabled:
            error_log(e, level=level)
