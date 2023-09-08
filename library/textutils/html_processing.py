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
        elif el.name == 'p' and 'ref' in el.attrs.get('class', []):
            el.name = 'ref'
        elif el.name == 'disp-formula':
            el.name = 'formula'
        if 'href' in el.attrs:
            el.attrs = {'href': el.attrs['href']}
        else:
            el.attrs = {}
    return soup


def headerize_headers(soup):
    for el in soup.find_all():
        if el.name == 'p':
            children = list(el.children)
            if len(children) == 1 and children[0].name == 'b':
                new_header = children[0]
                new_header.name = 'header'
                el.replace_with(new_header)
    return soup
