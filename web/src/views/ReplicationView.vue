<template lang="pug">
.container
  span(v-html="get_label('replicate_intro')")
  h5.mt-2 Light STC Mode
  p
    i Level: Easy
  p This mode involves replicating search metadata through IPFS.
  ul
    li Install any IPFS-compatible software such as <a href="https://github.com/ipfs/kubo">Kubo</a>
    li Pin <code>{{ web_ipfs_hash }}</code>. It also significantly improves the performance of searches you do using web-interface
  h5.mt-2 Full STC Mode
  p
    i Level: Advanced
  p This mode involves replicating search metadata, setting up a Summa search server and optionally accessing local data
  ul
    li Follow the <a href="https://izihawa.github.io/summa/quick-start">Quick Start guide</a> to deploy Summa server.
    li After installation, explore the <a href="/data">/data</a> subdirectory and attach indices to Summa:
      p.mt-2
        code
          p
            div # Pull Docker image
            div docker pull izihawa/summa-server:testing
          p
            div # Create data directory
            div mkdir -p data/bin
          p
            div # Download database
            div ipfs get {{ web_ipfs_hash }}data/nexus_science -o data/bin/nexus_science
          p
            div # Generate default Summa config
            div docker run izihawa/summa-server:testing generate-config -d /data -a 0.0.0.0:8082 > data/summa.yaml
          p
            div # Launch Summa
            div docker run -v $(pwd)/data:/data -p 8082:8082 -e RUST_BACKTRACE=1 izihawa/summa-server:testing serve /data/summa.yaml
          p
            div # Install Python client
            div pip install aiosumma
          p
            div # Attach index
            div summa-cli 0.0.0.0:8082 attach-index nexus_science '{"file": {}}'
          p
            div # Search by text
            div summa-cli 0.0.0.0:8082 search '[{"index_alias": "nexus_science", "query": {"match": {"value": "hemoglobin"}}, "collectors": [{"top_docs": {"limit": 10}}]}]'
            div $ Search by DOI
            div summa-cli 0.0.0.0:8082 search '[{"index_alias": "nexus_science", "query": {"term": {"field": "doi", "value": "10.1016/j.compbiomed.2023.106791"}}, "collectors": [{"top_docs": {"limit": 10}}]}]'
            div $ Search with OCRed content
            div summa-cli 0.0.0.0:8082 search '[{"index_alias": "nexus_science", "query": {"exists": {"field": "content"}}, "collectors": [{"top_docs": {"limit": 10}}]}]'
          p
            div # You may also download scholarly paper by their DOI
            div summa-cli 0.0.0.0:8082 search '[{"index_alias": "nexus_science", "query": {"term": {"field": "doi", "value": "10.1016/j.compbiomed.2023.106791"}}, "collectors": [{"top_docs": {"limit": 1}}]}]' | jq -r '.collector_outputs[0].documents.scored_documents[0].document' | jq -r '. | "\(.doi) \(.cid)"' | xargs -L1 bash -c 'ipfs get $1 -o $(echo -n $0 | jq -sRr @uri).pdf'
            div # or by any search query what allows you to store collections by topic
            div summa-cli 0.0.0.0:8082 search '[{"index_alias": "nexus_science", "query": {"boolean": {"subqueries": [{"occur": "should", "query": {"match": {"value": "cancer"}}}, {"occur": "must", "query": {"exists": {"field": "cid"}}}]}}, "collectors": [{"top_docs": {"limit": 1}}]}]' | jq -r '.collector_outputs[0].documents.scored_documents[].document' | jq -r '. | "\(.doi) \(.cid)"' | xargs -L1 bash -c 'ipfs get $1 -o $(echo -n $0 | jq -sRr @uri).pdf'
  h5.mt-2 Setting your own gateway
  p
    i Level: Hard
  p Your own gateway allows to access STC for people without IPFS. It requires your own domain name, installed Nginx reverse proxy and server with the good bandwidth.
  ul
    li Follow "Light STC Mode" guide
    li Install Nginx server with the following config
      p.mt-2
        code
          div server {
          div &nbsp;server_name example.org;
          div &nbsp;listen 443 ssl;
          div &nbsp;ssl_certificate /etc/ssl/private/example.org.cert;
          div &nbsp;ssl_certificate_key /etc/ssl/private/example.org.key;
          div &nbsp;ssl_protocols       TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
          div &nbsp;ssl_ciphers         HIGH:!aNULL:!MD5;
          div &nbsp;location /ipfs/ {
          div &nbsp;&nbsp;proxy_pass http://127.0.0.1:8080/ipfs/;
          div &nbsp;}
          div &nbsp;location / {
          div &nbsp;&nbsp;proxy_pass http://127.0.0.1:8080/;
          div &nbsp;&nbsp;proxy_set_header Host standard-template-construct.org;
          div &nbsp;}
          div }
  span(v-html="get_label('replicate_replicate_data')")
</template>
<script lang="ts">
import { defineComponent } from "vue";
import {get_label} from "@/translations";
export default defineComponent({
  name: "ReplicationView",
  data() {
    return {
      is_loading: false,
      web_ipfs_hash: "",
    };
  },
  created() {
    document.title = `Replication - STC`;
    fetch("/").then((r) => {
      this.web_ipfs_hash = r.headers.get("x-ipfs-path") || "";
    });
  }
});
</script>
<style lang="scss" scoped>
#origin {
  border-width: 10px;
  border-image: conic-gradient(blue, yellow, lime, aqua, yellow, magenta, blue)
    1;
  border-style: solid;
}
</style>
