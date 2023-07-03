import base64
import binascii
import logging

import base36
from izihawa_utils.exceptions import BaseError
from telethon import Button

from tgbot.translations import t


class TooLongQueryError(BaseError):
    level = logging.WARNING
    code = 'too_long_query_error'


class DecodeDeepQueryError(BaseError):
    level = logging.WARNING
    code = 'decode_deep_query_error'


def vote_button(language: str, case: str):
    label = f"REPORT_{case.upper()}_FILE"
    case = {'correct': 'c', 'incorrect': 'i'}[case]
    return Button.inline(
        text=t(label, language),
        data=f'/vote_{case}',
    )


def encode_query_to_deep_link(query, bot_name):
    encoded_query = encode_deep_query(query)
    if len(encoded_query) <= 64:
        return f'https://t.me/{bot_name}?start={encoded_query}'
    raise TooLongQueryError()


def to_bytes(n):
    return [n & 255] + to_bytes(n >> 8) if n > 0 else []


def recode_base36_to_base64(query):
    return base64.b64encode(bytearray(to_bytes(base36.loads(query))), altchars=b'-_').rstrip(b'=')


def recode_base64_to_base36(query):
    try:
        # Padding fix
        return base36.dumps(int.from_bytes(base64.b64decode(query + "=" * ((4 - len(query) % 4) % 4), altchars=b'-_'), 'little'))
    except (binascii.Error, ValueError, UnicodeDecodeError) as e:
        raise DecodeDeepQueryError(nested_error=e)


def encode_deep_query(query):
    return base64.b64encode(query.encode(), altchars=b'-_').decode()


def decode_deep_query(query):
    try:
        # Padding fix
        return base64.b64decode(query + "=" * ((4 - len(query) % 4) % 4), altchars=b'-_').decode()
    except (binascii.Error, ValueError, UnicodeDecodeError) as e:
        raise DecodeDeepQueryError(nested_error=e)


async def remove_button(event, mark, and_empty_too=False, link_preview=None):
    original_message = await event.get_message()
    if original_message:
        original_buttons = original_message.buttons
        buttons = []
        for original_line in original_buttons:
            line = []
            for original_button in original_line:
                if mark in original_button.text or (and_empty_too and not original_button.text.strip()):
                    continue
                line.append(original_button)
            if line:
                buttons.append(line)
        await event.edit(original_message.text, buttons=buttons, link_preview=link_preview)


def get_formatted_filesize(filesize) -> str:
    if filesize:
        filesize = max(1024, filesize)
        return '{:.1f}Mb'.format(float(filesize) / (1024 * 1024))
    else:
        return ''


def encode_link(bot_name, text, query) -> str:
    try:
        encoded_query = encode_query_to_deep_link(query, bot_name)
        if text:
            return f'[{text}]({encoded_query})'
        else:
            return encoded_query
    except TooLongQueryError:
        return text


def add_expand_dot(text, le: int):
    if len(text) < le:
        return text
    crop_at = text[:le].rfind(' ')
    return text[:crop_at] + '...'
