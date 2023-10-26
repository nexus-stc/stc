<template lang="pug">
div
  h3(v-html="document.title")
  .mt-1
    div(v-html="coordinates")
  .text-secondary
      span(v-html="extras")
  img.mt-3.img-thumbnail(v-if="!is_default_cover" width="160" :src="cover")
  .mt-3
    tags-list(:tags="document.tags")
  div(v-if="view")
    hr
    div.content-view(v-html="view")
  .clearfix
  .text-end.mt-4
    document-buttons(:http_links="http_links" :query="id_query()")
  .mt-3(v-if="referenced_bys.length > 0 || is_references_loading")
    b Referenced by
    .card.mt-3
      .card-body
        div
          div(v-if="referenced_bys.length > 0")
            references-list(:references="referenced_bys")
            .d-grid(v-if="has_next")
              hr
              button.btn.btn-sm.btn-secondary(v-if="!is_references_loading" v-on:click="limit += 5; find_references()") {{ get_label('load_more') }}...
              button.btn.btn-sm.btn-secondary(v-else) {{ get_label('loading') + '...' }}
          loading-spinner(v-else-if="is_references_loading && referenced_bys.length === 0").mt-3.mb-3
          span(v-else) No references have been found
</template>

<script lang="ts">
import { defineComponent } from 'vue'

import ConnectivityIssuesView from '@/components/ConnectivityIssues.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import BaseDocument from "@/components/BaseDocument.vue";
import DocumentButtons from "@/components/DocumentButtons.vue";
import TagsList from "@/components/TagsList.vue";
import ReferencesList from "@/components/ReferencesList.vue";
import CryptoJS from "crypto-js"

function render_wiki(document) {
  const parser = new DOMParser();
  const html_doc = parser.parseFromString(
      "<html><body>"
      + (document.abstract.replace(/<\/?abstract>/, '') || "")
      + (document.content.replace(/<\/?content>/, '') || "")
      + "</body></html>",
      'text/html');
  for (const link of Array.from(html_doc.getElementsByClassName("reference"))) {
    link.remove();
  }
  for (const link of html_doc.links) {
    const href = link.getAttribute("href");
    if (!href.startsWith("http"))  {
      const md5 = CryptoJS.MD5("A/" + href).toString()
      link.setAttribute("href", `/#/nexus_science/id.wiki:${md5}`);
    }
  }
  for (const image of html_doc.images) {
    const src = image.getAttribute("src");
    if (!src.startsWith("http")) {
      image.setAttribute("src", `/images/wiki/${src}`);
    }
    if (image.parentElement.className === "thumbinner") {
      image.parentElement.style.width = image.getAttribute("width");
    }
  }
  for (let trow of html_doc.getElementsByClassName("tmulti")) {
    let total_width = 0;
    for (const image of trow.getElementsByTagName("img")) {
      total_width += Number.parseInt(image.getAttribute("width"));
    }
    (trow as HTMLElement).style.width = total_width + "px";
  }
  for (let tooltip of html_doc.getElementsByClassName("tooltip")) {
    tooltip.removeAttribute("class");
  }
  return html_doc.firstChild.outerHTML
}

export default defineComponent({
  name: 'Document',
  extends: BaseDocument,
  components: {
    ConnectivityIssuesView,
    DocumentButtons,
    LoadingSpinner,
    ReferencesList,
    TagsList,
  },
  data () {
    return {
      is_references_loading: false,
      referenced_bys: [],
      has_next: false,
      references_limit: 5
    }
  },
  async created () {
    this.find_references()
  },
  computed: {
    view() {
      if (this.document.type === "wiki") {
        return render_wiki(this.document)
      }
      return this.document.abstract
    }
  },
  methods: {
    async find_references () {
      const dois = this.get_attr("dois")
      if (!dois || dois.length == 0) {
        return
      }
      try {
        this.is_references_loading = true
        const response = await this.search_service.search(`rd:${dois[0]}`, {
          page: 1,
          page_size: this.references_limit,
          index_name: this.index_name
        })
        this.referenced_bys =
          response[0].collector_output.documents.scored_documents
      } finally {
        this.is_references_loading = false
      }
    }
  }
})
</script>
