<template lang="pug">
div
  .row
    .col-3.col-lg-2(v-if="with_cover && cover")
      a(:href="item_link()")
        img.mb-3.img-thumbnail(width="100" :src="cover")
    .col-9.col-lg-10
      a.text-decoration-none.h5(v-if="with_large_caption" v-html="prepared_title" :href="item_link()")
      a.text-decoration-none.h6(v-else v-html="prepared_title" :href="item_link()")
      .mt-1(v-html="coordinates")
      .text-secondary(v-if="with_extras")
        span(v-html="extras")
        span(v-if="has_bookmark") &nbsp;|&nbsp;
          i.bi-bookmark-check-fill
  .row
    .col-12
      .mt-2(v-if="with_abstract && prepared_snippets", v-html="prepared_snippets")
      .mt-2(v-if="with_tags")
        tags-list(:tags="small_tags")
</template>

<script lang="ts">
import { defineComponent } from 'vue'

import BaseDocument from "@/components/BaseDocument.vue";
import { user_db } from "@/database";
import {decode_html, extract_text_from_html, remove_unpaired_escaped_tags} from "@/utils";

export default defineComponent({
  name: 'DocumentSnippet',
  components: { BaseDocument },
  extends: BaseDocument,
  props: {
    with_abstract: {
      type: Boolean,
      required: false,
      default: true
    },
    with_cover: {
      type: Boolean,
      required: false,
      default: false
    },
    with_extras: {
      type: Boolean,
      required: false,
      default: true
    },
    with_large_caption: {
      type: Boolean,
      required: false,
      default: false
    },
    with_tags: {
      type: Boolean,
      required: false,
      default: true
    },
    snippets: {
      type: Object
    }
  },
  data () {
    return {
      has_bookmark: false,
    }
  },
  async created () {
    this.has_bookmark = await user_db.has_bookmark(
      "nexus_science",
      this.id_query()
    )
  },
  computed: {
    prepared_snippets () {
      if (!this.document.abstract) {
        return null
      }
      let abstract = "";
      if (this.snippets.abstract) {
        abstract = this.snippets.abstract.html;
      }
      if (abstract.length === 0) {
        abstract = this.document.abstract.substring(0, 400)
        if (this.document.abstract.length > 400) {
          abstract += '...'
        }
        abstract = abstract.replace( /(<([^>]+)>)/ig, '');
        abstract = abstract.replace(/&lt;.*?&gt;/g, "")
      } else {
        const encoder = new TextEncoder()
        const original_length = encoder.encode(this.document.abstract).length
        const snippet_length =
          this.snippets.abstract.fragment.length

        if (original_length > snippet_length) {
          abstract += '...'
        }
        const full_decoded_abstract = extract_text_from_html(this.document.abstract)
        abstract = abstract.replace(/&lt;.*?&gt;/g, "");
        const snippet_decoded_abstract = extract_text_from_html(abstract)
        if (full_decoded_abstract.substring(0, 32) !== snippet_decoded_abstract.substring(0, 32)) {
          abstract = '...' + abstract
        }
      }
      return abstract
    },
    prepared_title () {
      let title = (this.document.title || 'No title').slice(0, this.max_title_length)
      if (
        this.snippets &&
        this.snippets.title &&
        this.snippets.title.html &&
        this.snippets.title.html.length > 0
      ) {
        title = this.snippets.title.html
      }
      const encoder = new TextEncoder()
      const original_length = encoder.encode(this.document.title).length
      if (original_length > this.max_title_length) {
        title += '...'
      }
      return decode_html(remove_unpaired_escaped_tags(title))
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
