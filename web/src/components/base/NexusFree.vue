<script lang="ts">
// @ts-nocheck
import { defineComponent } from "vue";
import BaseDocument from "./Document.vue";
import { format_bytes, generate_filename, generate_cid_external_links, cid_local_link } from "@/utils";
import TagsList from "../TagsList.vue";

export default defineComponent({
  extends: BaseDocument,
  name: "BaseNexusFree",
  data() {
    return {
      index_name: "nexus_free",
    };
  },
  components: { TagsList },
  computed: {
    coordinates() {
      let parts = []
      if (this.authors) {
        parts.push(this.authors)
      }
      const publisher = this.get_attr("publisher");
      if (publisher) {
        parts.push("by")
        parts.push(`<a class="text-decoration-none fst-italic link-secondary" href='/#/?q=metadata.publisher:"${publisher}"&ds=true'>${publisher}</a>`)
      }
      const series = this.get_attr("series");
      if (series) {
        parts.push("of")
        parts.push(`<a class="text-decoration-none fst-italic link-secondary" href='/#/?q=metadata.series:"${series}"&ds=true'>${series}</a>`)
      }
      if (this.formatted_date) {
        parts.push("on")
        parts.push(this.formatted_date);
      }
      return parts.join(" ");
    },
    extras() {
      const parts = [];
      const isbns = this.get_attr("isbns");
      if (isbns && isbns.length > 0) {
        parts.push(isbns.slice(0, 2).join(" - "));
      }
      if (this.filesize && this.filesize > 0) {
        parts.push(format_bytes(this.filesize));
      }
      if (this.first_link) {
        parts.push(this.first_link.extension);
      }
      if (this.document.language) {
        parts.push(this.document.language);
      }
      parts.push(this.icon);
      if (this.first_link) {
        const url = cid_local_link(this.first_link.cid, this.filename + "." + this.first_link.extension);
        parts.push(
          `<a class="bi bi-globe2 text-decoration-none link-secondary" href="${url.url}" target="_blank"></a>`
        )
      }
      return parts.join(" | ");
    },
    filename() {
      return generate_filename(this.document.title);
    },
    filesize() {
      return this.document.filesize;
    },
    formatted_date() {
      if (!this.issued_at || this.issued_at == -62135596800) {
        return;
      }
      const date = new Date(this.issued_at * 1000);
      return date.getFullYear();
    },
    external_links() {
      let external_links = [];
      if (this.first_link) {
        external_links.push(...generate_cid_external_links(this.first_link.cid, this.filename + "." + this.first_link.extension));
      }
      return external_links;
    },
    snippet() {
      if (this.document.abstract === undefined) {
        return "";
      }
      let abstract = this.scored_document.snippets.abstract.html;
      if (abstract.length === 0) {
        abstract = this.document.abstract.substring(0, 400);
        if (this.document.abstract.length > 400) {
          abstract += "...";
        }
      } else {
        let encoder = new TextEncoder();
        const original_length = encoder.encode(
          this.document.abstract
        ).length;
        const snippet_length =
          this.scored_document.snippets.abstract.fragment.length;
        if (original_length > snippet_length) {
          abstract += "...";
        }
        if (abstract[0] == abstract[0].toLowerCase()) {
          abstract = "..." + abstract;
        }
      }
      return abstract;
    },
    tags() {
      if (this.document.tags) {
        return `${this.document.tags.join(" - ")}`;
      } else {
        return null;
      }
    },
  },
});
</script>
