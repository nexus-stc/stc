from typing import (
    List,
    Optional,
)

from aiosumma import SummaClient

TEMPORAL_RANKING_FORMULA = "original_score * custom_score * fastsigm(abs(now - issued_at) / (86400 * 3) + 5, -1)"
PR_TEMPORAL_RANKING_FORMULA = f"{TEMPORAL_RANKING_FORMULA} * 1.96 * fastsigm(iqpr(quantized_page_rank), 0.15)"


default_field_aliases = {
    'author': 'authors.family',
    'authors': 'authors.family',
    'cid': 'links.cid',
    'doi': 'id.dois',
    'ev': 'metadata.event.name',
    'extension': 'links.extension',
    'format': 'links.extension',
    'isbn': 'metadata.isbns',
    'isbns': 'metadata.isbns',
    'issn': 'metadata.issns',
    'issns': 'metadata.issns',
    'lang': 'languages',
    'pub': 'metadata.publisher',
    'rd': 'references.doi',
    'ser': 'metadata.series',
}


default_term_field_mapper_configs = {
    'doi': {'fields': ['id.dois']},
    'doi_isbn': {'fields': ['metadata.isbns']},
    'isbn': {'fields': ['metadata.isbns']},
}


default_field_boosts = {
    'authors': 1.7,
    'extra': 1.7,
    'title': 1.7,
}


async def get_documents_on_topic(
    summa_client: SummaClient,
    topic: str,
    documents: int = 20,
    index_alias: str = 'nexus_science',
    ranking_formula: Optional[str] = None,
    is_fieldnorms_scoring_enabled: bool = False,
    default_fields: List[str] = ("abstract", "title", "content"),
):
    return await summa_client.search_documents({
        "index_alias": index_alias,
        "query": {"boolean": {"subqueries": [{
            "occur": "should",
            "query": {
                "match": {
                    "value": topic,
                    "query_parser_config": {
                        "default_fields": list(default_fields),
                        "field_aliases": default_field_aliases,
                        "field_boosts": default_field_boosts,
                    },
                }
            },
        }]}},
        "collectors": [{"top_docs": {"limit": documents, "scorer": {
            "eval_expr": ranking_formula or PR_TEMPORAL_RANKING_FORMULA,
        }}}],
        "is_fieldnorms_scoring_enabled": is_fieldnorms_scoring_enabled,
    })


def get_full_query_parser_config(query_language: Optional[str] = None):
    query_parser_config = {
        'default_fields': ['abstract', 'concepts', 'content', 'extra', 'title'],
        'term_limit': 20,
        'field_aliases': default_field_aliases,
        'field_boosts': default_field_boosts,
        'exact_matches_promoter': {
            'slop': 0,
            'boost': 2.0,
            'fields': ['abstract', 'extra', 'title']
        }
    }
    if query_language:
        query_parser_config['query_language'] = query_language
    return query_parser_config


def get_light_query_parser_config(query_language: Optional[str] = None):
    query_parser_config = {
        'default_fields': ['abstract', 'title'],
        'term_limit': 20,
        'field_aliases': default_field_aliases,
        'field_boosts': default_field_boosts,
    }
    if query_language:
        query_parser_config['query_language'] = query_language
    return query_parser_config


def get_query_parser_config(profile: str, query_language: Optional[str] = None):
    if profile == 'full':
        return get_full_query_parser_config(query_language)
    elif profile == 'light':
        return get_light_query_parser_config(query_language)
    else:
        raise ValueError("Unknown profile")


def get_default_scorer(profile: str):
    if profile == 'full':
        return {'eval_expr': PR_TEMPORAL_RANKING_FORMULA}
    elif profile == 'light':
        return None
    else:
        raise ValueError("Unknown profile")


def format_document(document: dict):
    parts = []
    if title := document.get('title'):
        parts.append(f'Title: {title}')
    if authors := document.get('authors'):
        parts.append(f'Authors: {authors}')
    if id_ := document.get('id'):
        parts.append(f'ID: {id_}')
    if links := document.get('links'):
        parts.append(f'Links: {links}')
    if abstract := document.get('abstract'):
        parts.append(f'Abstract: {abstract[:200]}')
    return '\n'.join(parts)


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

    def get_link_with_extension(self, extension, from_end: bool = False):
        links = self.links
        if from_end:
            links = reversed(self.links)
        for cid in links:
            full_link = self.stored_cids[cid]
            if full_link['extension'] == extension:
                return full_link

    def get_first_link(self):
        if self.links:
            return self.stored_cids[self.links[0]]
