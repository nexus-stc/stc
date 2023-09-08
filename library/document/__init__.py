from urllib.parse import quote

from library.textutils.utils import cast_string_to_single_string


class BaseDocumentHolder:
    def __init__(self, document):
        self.document = document

    def __getattr__(self, name):
        if name in self.document:
            return self.document[name]
        elif 'metadata' in self.document and name in self.document['metadata']:
            return self.document['metadata'][name]
        elif 'id' in self.document and name in self.document['id']:
            return self.document['id'][name]

    def has_cover(self):
        return bool(self.isbns and len(self.isbns) > 0)

    def get_links(self):
        if self.has_field('links') and self.links:
            return LinksWrapper(self.links)
        return LinksWrapper([])

    @property
    def ordered_links(self):
        links = self.get_links()
        pdf_link = None
        epub_link = None
        other_links = []
        for link in links.links:
            if link['extension'] == 'pdf' and not pdf_link:
                pdf_link = link
            elif link['extension'] == 'pdf' and not epub_link:
                epub_link = link
            else:
                other_links.append(link)
        if epub_link:
            other_links = [epub_link] + other_links
        if pdf_link:
            other_links = [pdf_link] + other_links
        return other_links


    @property
    def doi(self):
        if self.has_field('dois') and self.dois:
            return self.dois[0]

    def get_purified_name(self, link):
        limit = 55
        filename = cast_string_to_single_string(
            self.view_builder().add_authors(et_al=False).add_title(bold=False).add_formatted_datetime(
                with_months_for_recent=False).build().lower()
        )

        chars = []
        size = 0
        hit_limit = False

        for c in filename:
            current_size = size + len(c.encode())
            if current_size > limit:
                hit_limit = True
                break
            chars.append(c)
            size = current_size

        filename = ''.join(chars)
        if hit_limit:
            glyph = filename.rfind('-')
            if glyph != -1:
                filename = filename[:glyph]

        if not filename and self.doi:
            filename = quote(self.doi, safe='')
        if not filename:
            filename = link['cid']
        return filename

    def has_field(self, name):
        return (
            name in self.document
            or name in self.document.get('metadata', {})
            or name in self.document.get('id', {})
        )

    def get_internal_id(self):
        if self.doi:
            return f'id.dois:{self.doi}'
        elif self.nexus_id:
            return f'id.nexus_id:{self.nexus_id}'
        elif self.internal_iso:
            return f'id.internal_iso:{self.internal_iso}'
        elif self.internal_bs:
            return f'id.internal_bs:{self.internal_bs}'
        elif self.arc_ids:
            return f'id.arc_ids:{self.arc_ids[-1]}'
        elif self.libgen_ids:
            return f'id.libgen_ids:{self.libgen_ids[-1]}'
        elif self.zlibrary_ids:
            return f'id.zlibrary_ids:{self.zlibrary_ids[-1]}'
        else:
            return None


class LinksWrapper:
    def __init__(self, links):
        self.links = []
        self.stored_cids = {}
        for link in links:
            self.add(link)

    def reset(self):
        self.links = []
        self.stored_cids = {}

    def to_list(self):
        links = []
        visited = set()
        for other_link in self.links:
            if other_link not in visited:
                links.append(self.stored_cids[other_link])
            visited.add(other_link)
        return links

    def add(self, link):
        if link['cid'] in self.stored_cids:
            old_link = self.stored_cids[link['cid']]
            self.stored_cids[link['cid']] = link
            return old_link
        self.stored_cids[link['cid']] = link
        self.links.append(link['cid'])

    def prepend(self, link):
        if link['cid'] in self.stored_cids:
            self.stored_cids[link['cid']] = link
            self.links.remove(link['cid'])
        else:
            self.stored_cids[link['cid']] = link
        self.links = [link['cid']] + self.links

    def remove_cid(self, cid):
        found_link = None
        old_links = self.to_list()
        self.reset()
        for link in old_links:
            if link['cid'] == cid:
                found_link = link
            else:
                self.add(link)
        return found_link

    def get_link_with_extension(self, extension, from_end=False):
        links = self.links
        if from_end:
            links = reversed(self.links)
        for cid in links:
            full_link = self.stored_cids[cid]
            if full_link['extension'] == extension:
                return full_link
