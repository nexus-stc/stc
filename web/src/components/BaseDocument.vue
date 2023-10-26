<script lang="ts">
import { defineComponent } from 'vue'

import {
  default_cover,
  decode_html,
  remove_unpaired_escaped_tags,
  format_bytes,
  generate_filename
} from '@/utils'
import TagsList from "@/components/TagsList.vue";
import {utils} from "summa-wasm";

const default_icon = '📝'
type Author = { family: string, given: string, name: string, orcid: string }
const type_icons: {
  [key: string]: string;
} = {
  'book': '📚',
  'book-chapter': '🔖',
  'chapter': '🔖',
  'dataset': '📊',
  'component': '📊',
  'dissertation': '🧑‍🎓',
  'edited-book': '📚',
  'journal-article': '🔬',
  'monograph': '📚',
  'peer-review': '🤝',
  'proceedings': '📚',
  'proceedings-article': '🔬',
  'reference-book': '📚',
  'report': '📝',
  'standard': '🛠',
  'wiki': '📙'
}

function get_type_icon (type_name: string) {
  if (type_name === undefined) {
    return;
  }
  return type_icons[type_name] ?? default_icon
}

export function cid_local_link (cid: string, filename: string) {
  const { ipfs_hostname, ipfs_http_protocol } = utils.get_ipfs_hostname()
  return new HttpFileLink(`${ipfs_http_protocol}//${ipfs_hostname}/ipfs/${cid}?filename=${filename}`, 'Local IPFS');
}

export class HttpFileLink {
  url: string;
  label: string;

  constructor(url: string, label: string) {
    this.url = url;
    this.label = label;
  }
}

export class FileLinksGroup {
  cid: string;
  label: string;
  filename: string;
  local_http_file_link?: HttpFileLink;
  http_file_links: HttpFileLink[];

  constructor(cid: string, label: string, filename: string) {
    this.cid = cid;
    this.label = label;
    this.filename = filename;
    this.http_file_links = [];
  }

  all_links() {
    let links = [];
    if (this.local_http_file_link) {
      links.push(this.local_http_file_link)
    }
    if (this.http_file_links.length > 0) {
      links.push(...this.http_file_links)
    }
    return links;
  }
  first_link() {
    const all_links = this.all_links();
    if (all_links.length > 0) {
      return all_links[0];
    }
  }
  first_external_link() {
    if (this.http_file_links.length > 0) {
      return this.http_file_links[0];
    }
  }
}

export class HttpLinks {
  file_links_groups: FileLinksGroup[];
  external_sources: HttpFileLink[];
  constructor() {
    this.file_links_groups = [];
    this.external_sources = [];
  }
  add_external_sources(dois, issued_at) {
    if (dois && dois.length > 0) {
      if (issued_at < 1640984400) {
        const doi = dois[0];
        this.external_sources.push(new HttpFileLink(
            `https://sci-hub.se/${doi}`,
            "Sci-Hub.se",
        ));
        this.external_sources.push(new HttpFileLink(`http://library.lol/scimag/${doi}`, "Library.lol"));
      }
    }
  }
  add_file(cid: string, label: string, filename: string) {
    let file = new FileLinksGroup(cid, label, filename);
    file.local_http_file_link = cid_local_link(cid, filename);
    file.http_file_links.push(...[
      new HttpFileLink(
        `https://${cid}.ipfs.w3s.link/?filename=${filename}`,
        'Web3 Storage',
      ),
      new HttpFileLink(
        `https://cloudflare-ipfs.com/ipfs/${cid}?filename=${filename}`,
        'CloudFlare IPFS'
      ),
      new HttpFileLink(
        `https://ipfs.io/ipfs/${cid}?filename=${filename}`,
        'IPFS.io'
      )
    ]);
    this.file_links_groups.push(file);
  }
  first_file_links_group() {
    if (this.file_links_groups.length > 0) {
      return this.file_links_groups[0]
    }
  }
  first_file_links_group_first_external_link() {
    if (this.file_links_groups.length > 0) {
      return this.file_links_groups[0].first_external_link();
    }
  }
  get_file_links_group_with_extension(extension) {
    for (const file_links_group of this.file_links_groups) {
      if (file_links_group.filename.endsWith(extension)) {
        return file_links_group;
      }
    }
  }

  is_empty() {
    for (const file_links_group of this.file_links_groups) {
      return false;
    }
    return true;
  }
}

export default defineComponent({
  name: 'BaseDocument',
  components: { TagsList },
  props: {
    document: {
      type: Object,
      required: true
    },
    with_tags: {
      type: Boolean,
      default: true
    }
  },
  data () {
    return {
      cover: default_cover,
      is_default_cover: true,
      max_title_length: 180,
    }
  },
  computed: {
    authors () {
      if (this.document.authors) {
        let authors = this.document.authors.slice(0, 3).map((author: Author) => {
          let plain_author = ''
          if (author.family && author.given) {
            plain_author = author.given + ' ' + author.family
          } else if (author.family || author.given) {
            plain_author = author.family || author.given
          } else if (author.name) {
            plain_author = author.name
          }
          if (plain_author && author.orcid) {
            return `<a class="text-decoration-none fst-italic" href='#/?q=authors.orcid:"${author.orcid}"&ds=true'>${plain_author}</a>`
          } else {
            return plain_author
          }
        }).join(', ')
        if (this.document.authors.length > 3) {
          authors += ' et al'
        }
        return authors
      }
      return null
    },
    container_title () {
      return this.get_attr('container_title');
    },
    coordinates () {
      const parts = []
      if (this.authors) {
        parts.push(this.authors)
      }
      const container_title = this.get_attr('container_title')
      if (container_title) {
        const publisher = this.get_attr('publisher')
        const series = this.get_attr('series')
        const issns = this.get_attr('issns')
        if (publisher) {
          parts.push('by')
          parts.push(`<a class="text-decoration-none fst-italic" href='#/?q=metadata.publisher:"${encodeURIComponent(publisher)}"'>${publisher}</a>`)
        }
        if (series) {
          parts.push('of')
          parts.push(`<a class="text-decoration-none fst-italic" href='#/?q=metadata.series:"${encodeURIComponent(series)}"&ds=true'>${series}</a>`)
        }
        parts.push('in')
        if (issns) {
          parts.push(`<a class="text-decoration-none fst-italic" href='#/?q=metadata.issns:"${encodeURIComponent(issns[0])}"&ds=true'>${container_title}</a>`)
        } else {
          parts.push(`<a class="text-decoration-none fst-italic" href='#/?q=metadata.container_title:"${encodeURIComponent(container_title)}"&ds=true'>${container_title}</a>`)
        }
      }
      if (this.volume_or_issue) {
        parts.push(this.volume_or_issue)
      }
      if (this.formatted_date) {
        parts.push('on')
        parts.push(this.formatted_date)
      }
      return parts.join(' ')
    },
    doi_link () {
      const dois = this.get_attr("dois");
      if (dois && dois.length > 0) {
        return `https://doi.org/${dois[0]}`
      }
    },
    extensions () {
      const e = new Set();
      for (const link of this.links) {
        e.add(link["extension"])
      }
      return Array.from(e).sort()
    },
    extras () {
      const parts = []
      const dois = this.get_attr("dois");
      if (dois && dois.length > 0) {
        parts.push(
          `<a class="text-decoration-none" href="${this.doi_link}" target="_blank">doi:${dois[0]}</a>`
        )
      }
      if (this.document.referenced_by_count) {
        parts.push(
          `<a class="text-decoration-none" href="#/?q=rd:${this.document.doi}&ds=true">🔗 ${this.document.referenced_by_count}</a>`
        )
      }
      for (const extension of this.extensions) {
        parts.push(extension);
      }
      if (this.first_link && this.links.length < 2 && this.first_link["filesize"] > 0) {
        parts.push(format_bytes(this.first_link["filesize"]))
      }
      if (this.document.languages) {
        parts.push(...this.document.languages)
      }
      parts.push(this.icon)
      const first_file_links_group = this.http_links.first_file_links_group();
      if (first_file_links_group !== undefined) {
        const link = first_file_links_group.first_link();
        if (link !== undefined) {
          parts.push(
            `<a class="bi bi-globe2 text-decoration-none" href="${link.url}" target="_blank"></a>`
          )
        }
      }
      return parts.join(' | ');
    },
    http_links() {
      const http_links = new HttpLinks();
      http_links.add_external_sources(this.get_attr("dois"), this.document.issued_at);

      for (const link of this.links) {
        const full_filename = this.filename + "." + link.extension;
        let label = link.extension.toUpperCase();
        if (link.filesize) {
          label += ` (${format_bytes(link.filesize, 1)})`
        }
        http_links.add_file(link.cid, label, full_filename)
      }
      return http_links
    },
    filename () {
      return generate_filename(this.document.title)
    },
    first_link () {
      for (const link of this.links) {
        return link
      }
    },
    formatted_date () {
      if (!this.issued_at || this.issued_at === -62135596800) {
        return
      }
      const date = new Date(this.issued_at * 1000)
      if (
        Math.abs(this.issued_at - Math.floor(Date.now() / 1000)) <
        3 * 365 * 24 * 60 * 60
      ) {
        return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
      }
      return date.getFullYear()
    },
    icon () {
      return get_type_icon(this.document.type)
    },
    issued_at () {
      return this.document.issued_at
    },
    links () {
      return this.document.links || [];
    },
    small_tags () {
      if (this.document.tags) {
        let tags = this.document.tags.filter((e) => { return e.length < 64 })
        return tags.slice(0, 7)
      }
      return []
    },
    title () {
      let title = (this.document.title || 'No title').slice(0, this.max_title_length)
      const encoder = new TextEncoder()
      const original_length = encoder.encode(this.document.title).length
      if (original_length > this.max_title_length) {
        title += '...'
      }
      return decode_html(remove_unpaired_escaped_tags(title))
    },
    volume_or_issue () {
      const issns = this.get_attr('issns')
      const issue = this.get_attr('issue')
      const volume = this.get_attr('volume')
      const with_link = issns && issns?.length > 0
      const filters = []
      let text = ''
      if (volume && issue) {
        text = `vol. ${volume}(${issue})`
      } else {
        if (volume) {
          text = `vol. ${volume}`
        }
        if (issue) {
          text = `iss. ${issue}`
        }
      }
      if (with_link) {
        filters.push(`metadata.issns:%2B"${issns[0]}"`)
        if (volume) {
          filters.push(`metadata.volume:%2B"${volume}"`)
        }
        if (issue) {
          filters.push(`metadata.issue:%2B"${issue}"`)
        }
        return `<a class="text-decoration-none fst-italic" href='#/?q=${filters.join('+')}&ds=true'>${text}</a>`
      } else {
        return text
      }
    },
  },
  async created () {
    if (this.document === undefined) {
      return;
    }
    const isbns = this.get_attr('isbns')
    if (isbns && isbns.length > 0) {
      const cover = await fetch('https://covers.openlibrary.org/b/isbn/' + isbns[0] + '-M.jpg')
      if (cover.ok) {
        const blob = await cover.blob()
        if (blob.type.startsWith('image')) {
          this.cover = URL.createObjectURL(blob)
          this.is_default_cover = false;
          return;
        }
      }
    }
  },
  methods: {
    format_bytes,
    get_attr (name: string) {
      if (name in this.document) {
        return this.document[name]
      } else if ('metadata' in this.document && name in this.document.metadata) {
        return this.document.metadata[name]
      } else if ('id' in this.document && name in this.document.id) {
        return this.document.id[name]
      }
    },
    id_query () {
      const dois = this.get_attr("dois");
      const internal_iso = this.get_attr("internal_iso");
      const internal_bs = this.get_attr("internal_bs");
      const pubmed_id = this.get_attr("pubmed_id");
      const ark_ids = this.get_attr("ark_ids");
      const libgen_ids = this.get_attr("libgen_ids");
      const zlibrary_ids = this.get_attr("zlibrary_ids");
      const nexus_id = this.get_attr("nexus_id");
      const wiki = this.get_attr("wiki");

      if (dois && dois.length > 0) {
        return `id.dois:${dois[0]}`;
      } else if (internal_iso) {
        return `id.internal_iso:${internal_iso}`;
      } else if (internal_bs) {
        return `id.internal_bs:${internal_bs}`;
      } else if (pubmed_id) {
        return `id.pubmed_id:${pubmed_id}`;
      } else if (ark_ids && ark_ids.length > 0) {
        return `id.ark_ids:${ark_ids[0]}`;
      } else if (zlibrary_ids && zlibrary_ids.length > 0) {
        return `id.zlibrary_ids:${zlibrary_ids[0]}`;
      } else if (libgen_ids && libgen_ids.length > 0) {
        return `id.libgen_ids:${libgen_ids[0]}`;
      } else if (nexus_id) {
        return `id.nexus_id:${nexus_id}`;
      } else if (wiki) {
        return `id.wiki:${wiki}`;
      } else if(this.first_link) {
        return 'cid:' + this.first_link.cid;
      }
    },
    item_link () {
      return `#/nexus_science/${this.id_query()}`
    },
  }
})
</script>

<style scoped lang="scss">
li {
  padding-bottom: 15px;
  padding-left: 0;
  &:after {
    content: none;
  }
}
</style>
