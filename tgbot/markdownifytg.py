import re

from markdownify import (
    MarkdownConverter,
    abstract_inline_conversion,
)

html_heading_re = re.compile(r'(h[1-6]|header)')


class Converter(MarkdownConverter):
    convert_b = abstract_inline_conversion(lambda self: '**')
    convert_i = abstract_inline_conversion(lambda self: '__')
    convert_em = abstract_inline_conversion(lambda self: '__')

    def convert_header(self, el, text, convert_as_inline):
        return super().convert_b(el, text, convert_as_inline) + '\n'


class SnippetConverter(MarkdownConverter):
    convert_highlight = abstract_inline_conversion(lambda self: '**')
    convert_i = abstract_inline_conversion(lambda self: '__')


md_converter = Converter(escape_asterisks=False)
highlight_md_converter = SnippetConverter(escape_asterisks=False)


def md(html, **options):
    return Converter(**options).convert(html)
