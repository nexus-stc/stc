<script lang="ts">
// @ts-nocheck
import { defineComponent } from "vue";
import { format_bytes } from "@/utils";


const default_icon = '📝'
const type_icons = {
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
}


function get_type_icon(type_) {
  return type_icons[type_] || default_icon;
}

export default defineComponent({
  name: "BaseDocument",
  props: {
    scored_document: {
      type: Object,
      required: true,
    },
    with_large_caption: {
      type: Boolean,
      default: true,
    },
    with_tags: {
      type: Boolean,
      default: true,
    },
  },
  async created() {
    const isbns = this.get_attr("isbns");
    if (isbns) {
      const cover = await fetch('https://covers.openlibrary.org/b/isbn/' + isbns[0] + '-M.jpg');
      if (cover.ok) {
        const blob = await cover.blob();
        if(blob.type.startsWith("image")) {
          this.cover = URL.createObjectURL(blob);
        }
      }
    }
  },
  data() {
    const document = JSON.parse(this.scored_document.document);
    return {
      cover: null,
      document: document,
    };
  },
  methods: {
    format_bytes: format_bytes,
    get_attr(name: string) {
      if (name in this.document) {
        return this.document[name]
      } else if ("metadata" in this.document && name in this.document.metadata) {
        return this.document.metadata[name]
      } else if ("id" in this.document && name in this.document.id) {
        return this.document.id[name]
      }
    },
    id_query() {
      if (this.first_link) {
        return "cid:" + this.first_link.cid
      }
    },
    item_link() {
      return `/#/${this.index_name}/${this.id_query()}`;
    },
  },
  computed: {
    authors() {
      if (this.document.authors) {
        let authors = this.document.authors.slice(0, 3).map((author) => {
          let plain_author = "";
          if (author.family && author.given) {
            plain_author = author.given + " " + author.family;
          } else if (author.family || author.given) {
            plain_author = author.family || author.given
          } else if (author.name) {
            plain_author = author.name;
          }
          if (plain_author && author.orcid) {
            return `<a class="text-decoration-none fst-italic link-secondary" href='/#/?q=authors.orcid:"${author.orcid}"&ds=true'>${plain_author}</a>`
          } else {
            return plain_author
          }
        }).join(", ");
        if (this.document.authors.length > 3) {
          authors += " et al";
        }
        return authors;
      }
      return null;
    },
    formatted_date() {
      if (!this.issued_at || this.issued_at == -62135596800) {
        return;
      }
      const date = new Date(this.issued_at * 1000);
      if (
        Math.abs(this.issued_at - Math.floor(Date.now() / 1000)) <
        3 * 365 * 24 * 60 * 60
      ) {
        return date.toLocaleDateString(undefined, {year: "numeric", month: "long", day: "numeric"});
      }
      return date.getFullYear();
    },
    icon() {
      return get_type_icon(this.document.type)
    },
    issued_at() {
      return this.document.issued_at;
    },
    small_tags() {
      if (this.document.tags) {
        return this.document.tags.slice(0, 7);
      }
      return [];
    },
    title() {
      let title = (this.document.title || "No title").slice(0, this.snippet_length);
      if (
        this.scored_document.snippets.title &&
        this.scored_document.snippets.title.html &&
        this.scored_document.snippets.title.html.length > 0
      ) {
        title = this.scored_document.snippets.title.html;
      }
      let encoder = new TextEncoder();
      const original_length = encoder.encode(this.document.title).length;
      if (original_length > this.snippet_length) {
        title += "...";
      }
      return title;
    },
    first_link() {
      if (this.document.links) {
        return this.document.links[0];
      }
    }
  },
});
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
