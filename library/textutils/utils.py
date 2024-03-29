import re
import struct

import isbnlib

from . import (
    EMAIL_REGEX,
    HASHTAG_REGEX,
    MULTIWHITESPACE_REGEX,
    NON_ALNUMWHITESPACE_REGEX,
    TELEGRAM_LINK_REGEX,
    URL_REGEX,
)


def add_surrogate(text):
    return ''.join(
        # SMP -> Surrogate Pairs (Telegram offsets are calculated with these).
        # See https://en.wikipedia.org/wiki/Plane_(Unicode)#Overview for more.
        ''.join(chr(y) for y in struct.unpack('<HH', x.encode('utf-16le')))
        if (0x10000 <= ord(x) <= 0x10FFFF) else x for x in text
    )


def cast_string_to_single_string(s):
    processed = MULTIWHITESPACE_REGEX.sub(' ', NON_ALNUMWHITESPACE_REGEX.sub(' ', s))
    processed = processed.strip().replace(' ', '-')
    return processed


def despace(text):
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n[ \t]+', '\n', text)
    return text


def despace_full(text):
    return re.sub(r'\s+', ' ', text).strip()


def despace_smart(text):
    text = re.sub(r'\n\s*[-•]+\s*', r'\n', text)
    text = re.sub(r'\n{2,}', '\n', text).strip()
    text = re.sub(r'\.?(\s+)?\n', r'. ', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def escape_format(text, escape_font=True, escape_quote=True, escape_brackets=True):
    if isinstance(text, str):
        if escape_font:
            text = re.sub(r'([_*]){2,}', r'\g<1>', text)
        if escape_quote:
            text = text.replace("`", "'")
        if escape_brackets:
            text = text.replace('[', r'`[`').replace(']', r'`]`')
    elif isinstance(text, bytes):
        if escape_font:
            text = re.sub(br'([_*]){2,}', br'\g<1>', text)
        if escape_quote:
            text = text.replace(b"`", b"'")
        if escape_brackets:
            text = text.replace(b'[', br'`[`').replace(b']', br'`]`')
    return text


def remove_markdown(text):
    text = re.sub('[*_~]{2,}', '', text)
    text = re.sub('`+', '', text)
    text = re.sub(r'\[\s*(.*?)(\s*)\]\(.*?\)', r'\g<1>\g<2>', text, flags=re.MULTILINE)
    return text


def remove_emails(text):
    return re.sub(EMAIL_REGEX, '', text)


def remove_hashtags(text):
    return re.sub(HASHTAG_REGEX, '', text)


def remove_hidden_chars(text):
    return text.replace('\xad', '')


def remove_url(text):
    return re.sub(URL_REGEX, '', text)


def replace_telegram_link(text):
    return re.sub(TELEGRAM_LINK_REGEX, r'@\1', text)


def split_at(s, pos):
    if len(s) < pos:
        return s
    pos -= 10
    pos = max(0, pos)
    for p in range(pos, min(pos + 20, len(s) - 1)):
        if s[p] in [' ', '\n', '.', ',', ':', ';', '-']:
            return s[:p] + '...'
    return s[:pos] + '...'


def unwind_hashtags(text):
    return re.sub(HASHTAG_REGEX, r'\2', text)


def process_isbns(isbnlikes):
    isbns = []
    for isbnlike in isbnlikes:
        if not isbnlike:
            continue
        if isbnlike[0].isalpha() and len(isbnlike) == 10 and isbnlike[1:].isalnum():
            isbns.append(isbnlike.upper())
            continue
        isbn = isbnlib.canonical(isbnlike)
        if not isbn:
            continue
        isbns.append(isbn)
        if isbnlib.is_isbn10(isbn):
            if isbn13 := isbnlib.to_isbn13(isbn):
                isbns.append(isbn13)
        elif isbnlib.is_isbn13(isbn):
            if isbn10 := isbnlib.to_isbn10(isbn):
                isbns.append(isbn10)
    return list(sorted(set(isbns)))
