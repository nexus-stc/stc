import logging

from izihawa_utils.exceptions import BaseError


class BannedUserError(BaseError):
    level = logging.WARNING
    code = 'banned_user_error'

    def __init__(self, ban_timeout: int):
        self.ban_timeout = ban_timeout


class UnknownFileFormatError(BaseError):
    level = logging.WARNING
    code = 'unknown_file_format_error'


class UnknownIndexAliasError(BaseError):
    code = 'unknown_index_alias_error'


class WidgetError(BaseError):
    level = logging.WARNING
    code = 'widget_error'

    def __init__(self, text, buttons):
        self.text = text
        self.buttons = buttons


class DownloadError(BaseError):
    level = logging.WARNING
    code = 'download_error'


class InvalidSearchError(BaseError):
    def __init__(self, search):
        self.search = search


class UnavailableSummaError(BaseError):
    pass
