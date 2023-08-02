import re

from library.textutils.utils import despace


def reduce_br(soup_str):
    soup_str = soup_str.replace("<br>", "<br/>").replace('<p><br/>', '<p>').replace('<br/></p>', '</p>')
    soup_str = re.sub(r'([^.>])<br/>([^(<br/>)])', r'\g<1> \g<2>', soup_str)
    soup_str = re.sub(r'(?:<br/>\s*)+([^(<br/>)])', r'<br/><br/>\g<1>', soup_str)
    soup_str = despace(soup_str)
    return soup_str


def remove_chars(soup_str):
    soup_str = soup_str.replace('\ufeff', '').replace('\r\n', '\n')
    return soup_str


def process_tags(soup):
    for el in soup.find_all():
        if el.name == 'span':
            el.unwrap()
        elif el.name == 'em':
            el.name = 'i'
        elif el.name == 'strong':
            el.name = 'b'
        elif el.name == 'sec':
            el.name = 'section'
        elif el.name in {'title', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            el.name = 'header'
        el.attrs = {}
    return soup
