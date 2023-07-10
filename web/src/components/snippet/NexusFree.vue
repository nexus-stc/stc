<template lang="pug">
.row
  .col-auto.me-n2.mt-n2.mb-n1(v-if="cover")
    a(:href="item_link()")
      img.img-thumbnail(width="54" :src="cover")
  .col(:class="{'ms-n1' : cover }")
    a.text-decoration-none.h6(v-if="with_large_caption" v-html="title" :href="item_link()")
    a.text-decoration-none.fw-bold(v-else v-html="title" :href="item_link()" style="color: inherit;")
    .small.mt-1(v-html="coordinates")
    .small.text-secondary(v-if="with_extras")
      span(v-html="extras")
      span(v-if="has_bookmark") &nbsp;|&nbsp;
        i.bi-bookmark-check-fill
.mt-2(v-if="with_abstract && snippet", v-html="snippet")
.small.clearfix(v-if="with_tags")
  .mt-2.text-secondary.float-start
    tags-list(:tags="small_tags")
</template>

<script lang="ts">
// @ts-nocheck
import { defineComponent } from "vue";
import BaseNexusFree from "@/components/base/NexusFree.vue";
import {user_db} from "@/database";

export default defineComponent({
  name: "NexusBookSnippet",
  extends: BaseNexusFree,
  props: {
    with_abstract: {
      type: Boolean,
      default: true,
    },
    with_extras: {
      type: Boolean,
      required: false,
      default: true,
    },
  },
  data() {
    return {
      has_bookmark: false,
      snippet_length: 180,
    };
  },
  async created() {
    this.has_bookmark = await user_db.has_bookmark(
      this.index_name,
      this.id_query()
    );
  },
});
</script>
