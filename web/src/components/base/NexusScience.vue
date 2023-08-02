<script lang="ts">
import { defineComponent } from 'vue'

import { cid_local_link, format_bytes, generate_cid_external_links, generate_filename } from '@/utils'

import TagsList from '../TagsList.vue'
import BaseDocument from './Document.vue'

export default defineComponent({
  name: 'BaseNexusScience',
  components: { TagsList },
  extends: BaseDocument,
  data () {
    return {
      index_name: 'nexus_science'
    }
  },
  computed: {
    container_title () {
      return this.get_attr('container_title')
    },
    doi_link () {
      return `https://doi.org/${this.document.doi}`
    },
    extras () {
      const parts = []
      if (this.document.doi) {
        parts.push(
          `<a class="text-decoration-none" href="${this.doi_link}">doi:${this.document.doi}</a>`
        )
      }
      if (this.document.referenced_by_count) {
        parts.push(
          `<a class="text-decoration-none" href="#/?q=rd:${this.document.doi}&ds=true">🔗 ${this.document.referenced_by_count}</a>`
        )
      }
      if (this.filesize && this.filesize > 0) {
        parts.push(format_bytes(this.filesize))
      }
      if (this.document.language) {
        parts.push(this.document.language)
      }
      parts.push(this.icon)
      if (this.first_link) {
        const url = cid_local_link(this.first_link.cid, this.filename + '.' + this.first_link.extension)
        parts.push(
          `<a class="bi bi-globe2 text-decoration-none" href="${url.url}" target="_blank"></a>`
        )
      }
      return parts.join(' | ')
    },
    filename () {
      return generate_filename(this.document.title)
    },
    filesize () {
      return this.document.filesize
    },
    external_links () {
      const external_links = []
      if (this.first_link) {
        external_links.push(...generate_cid_external_links(this.first_link.cid, this.filename + '.' + this.first_link.extension))
      }
      // If before 2022
      if (this.document.issued_at < 1640984400) {
        external_links.push({
          url: `https://sci-hub.se/${this.document.doi}`,
          name: 'Sci-Hub.se'
        })
      }
      external_links.push({
        url: `http://library.lol/scimag/${this.document.doi}`,
        name: 'Library.lol'
      })
      return external_links
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
    snippet () {
      if (!this.document.abstract) {
        return null
      }
      let abstract = this.scored_document.snippets.abstract.html
      if (abstract.length === 0) {
        abstract = this.document.abstract.substring(0, 400)
        if (this.document.abstract.length > 400) {
          abstract += '...'
        }
      } else {
        const encoder = new TextEncoder()
        const original_length = encoder.encode(this.document.abstract).length
        const snippet_length =
          this.scored_document.snippets.abstract.fragment.length
        if (original_length > snippet_length) {
          abstract += '...'
        }
        if (abstract[0] === abstract[0].toLowerCase()) {
          abstract = '...' + abstract
        }
      }
      return abstract
    },
    volume_or_issue () {
      const issns = this.get_attr('issns')
      const issue = this.get_attr('issue')
      const volume = this.get_attr('volume')
      const with_link = issns?.length > 0
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
    }
  },
  methods: {
    id_query () {
      return 'doi:' + this.document.doi
    }
  }
})
</script>
