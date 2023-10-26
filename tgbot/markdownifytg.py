import re

from markdownify import (
    MarkdownConverter,
    abstract_inline_conversion, chomp,
)

html_heading_re = re.compile(r'(h[1-6]|header|title)')


class Converter(MarkdownConverter):
    convert_b = abstract_inline_conversion(lambda self: '**')
    convert_i = abstract_inline_conversion(lambda self: '__')
    convert_em = abstract_inline_conversion(lambda self: '__')

    def convert_header(self, el, text, convert_as_inline):
        return '\n' + super().convert_b(el, text, convert_as_inline) + '\n'

    def convert_hn(self, n, el, text, convert_as_inline):
        return '\n' + super().convert_b(el, text, convert_as_inline) + '\n'

    def convert_hr(self,  el, text, convert_as_inline):
        return ''

    def convert_title(self, el, text, convert_as_inline):
        return super().convert_b(el, text, convert_as_inline) + '\n'

    def convert_formula(self, el, text, convert_as_inline):
        return '🔢\n'

    def convert_a(self, el, text, convert_as_inline):
        prefix, suffix, text = chomp(text)
        if not text:
            return ''
        href = el.get('href')
        return f'[{text}]({href})'

    def convert_img(self, el, text, convert_as_inline):
        return '🖼️\n'

    def convert_table(self, el, text, convert_as_inline):
        return '🔢\n'


class SnippetConverter(MarkdownConverter):
    convert_highlight = abstract_inline_conversion(lambda self: '**')
    convert_i = abstract_inline_conversion(lambda self: '')
    convert_header = abstract_inline_conversion(lambda self: '')

    def convert_hn(self, n, el, text, convert_as_inline):
        return text

    def convert_hr(self,  el, text, convert_as_inline):
        return ''

    def convert_title(self, el, text, convert_as_inline):
        return text

    def convert_formula(self, el, text, convert_as_inline):
        return '🔢\n'

    def convert_img(self, el, text, convert_as_inline):
        return '🖼️\n'

    def convert_table(self, el, text, convert_as_inline):
        return '🔢\n'


md_converter = Converter(escape_asterisks=False)
highlight_md_converter = SnippetConverter(escape_asterisks=False)


def md(html, **options):
    return Converter(**options).convert(html)
