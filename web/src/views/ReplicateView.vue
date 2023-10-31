<template lang="pug">
.container
  h3 {{ get_label ("set_up_your_own_replica") }}
  p The Standard Template Construct (STC) can be conveniently replicated on your personal computer or server. The STC consists of several critical components: search metadata, scholarly papers, and a web interface with a search engine (referred to as Web STC in subsequent references).
  p Replicating the search metadata and web interface can enhance your search performance. Simultaneously, replicating the scholarly papers can convert your computer into a comprehensive, standalone library.
  p To accomplish these tasks, you will need IPFS properly configured.
  h5 Set Up STC for Local Usage
  p IPFS is responsible for acquiring search metadata, scholarly papers, and the Web STC. The Web STC includes an embedded version of Summa Search, enabling you to have a full-fledged search function in your browser.
  h6 Step 1: Install IPFS
  p Follow the <a href="https://docs.ipfs.tech/install/command-line/#install-official-binary-distributions" target="_blank">official guide</a>. Ensure you select the correct binaries for your CPU architecture.
  h6 Step 2: Configure IPFS Settings
  p Here are the recommended settings, which have proven effective in real-world use. Commands should be executed in your Terminal:
  pre
    code
      | # set to the amount of disk space you wish to use
      | ipfs config Datastore.StorageMax 10TB
      | # set to the amount of RAM you wish to use
      | ipfs config Swarm.ResourceMgr.MaxMemory 16GB
      | ipfs config Routing.Type 'dhtclient'
      | ipfs config --json Experimental.OptimisticProvide true
      | ipfs config --json Routing.AcceleratedDHTClient true
      | ipfs config Reprovider.Interval --json '"23h"'
  p Set the environment variable <code>GOMEMLIMIT=16GB</code> (choose right amount for your server) before launching the daemon to limit memory usage.
  p It's also recommended to have a public address set in your config or ensure it's correctly broadcasted using the <code>ipfs id</code> command.
  h6 Step 3: Pin Search Metadata (optional)
  p Use the following command to start the pinning process of search metadata and the Web STC:
  pre ipfs pin add /ipns/libstc.cc --progress
  h6 Step 4a: Pin Stable Release of Scholarly Papers (optional)
  p Use the following command to start the pinning process for scholarly papers. The command takes a snapshot of previous scholarly papers, which might be slightly outdated and does not include items without a DOI.
  pre ipfs pin add /ipns/hub.standard-template-construct.org --progress
  h6 Step 4b: Pin Actual Scholarly Papers and Books (optional)
  p These commands require an installed version of Python. By the end, you will have all the items stored in STC pinned.
  pre
    code
      | pip install stc-geck
      | geck - documents | jq -r "select (.links != null) .links[].cid" | xargs -n 1 -P 8 -I{} ipfs pin add {} --timeout 600s
  p Congrats, you have your own STC. Ensure that you have installed <a href="#/help/install-ipfs">IPFS Companion</a> and open <a href="https://libstc.cc">Web STC</a>. It will be working as fast as possible.
  h5 Set Up for Family or Community Usage
  p This section describes how to configure STC for local usage based on the previous section, making it available over your local network or the Internet.
  p The recommended approach is to set up a reverse NGINX proxy for the IPFS daemon. This allows other servers to make requests to an STC instance.
  p Please note that it's essential to have SSL configured and a certificate for your domain name. Without a secure context, STC cannot function properly.
  h6 Set Up NGINX
  p Open and edit <code>/etc/nginx/sites-available/default</code> as shown below. Make sure to replace stc.local and the certificate paths with your own values:
  pre
    code
      | server {
      |     listen 443 ssl default_server;
      |     listen [::]:443 ssl;
      |     ssl_certificate stc-local.crt;
      |     ssl_certificate_key stc-local.key;
      |     server_name stc.local;
      |
      |     location / {
      |         proxy_pass http://localhost:8080;
      |         proxy_set_header Host $host;
      |         proxy_cache_bypass $http_upgrade;
      |         allow all;
      |     }
      | }
      | server {
      |     listen 80;
      |     server_name stc.local;
      |     return 301 https://stc.local$request_uri;
      | }
  h6 Adjust ~/.ipfs/config
  p For proper functionality with the public name, the IPFS daemon must be configured as well:
  pre
    code
      | {
      |  ...
      |   "Gateway": {
      |     ...
      |     "PublicGateways": {
      |       "stc.local": {
      |         "UseSubdomains": true,
      |         "Paths": ["/ipfs", "/ipns"]
      |       }
      |     },
      |     "RootRedirect": "/ipns/libstc.cc"
      |   }
      | ...
      | }
  h5 Set Up for Intense Processing
  p Sometimes, having the Web STC is not enough. For example, you might want to create a website on top of the STC or build Telegram Bot.
  p You have the opportunity to set up a search server with STC data, which can be used in your project. Below are several ways of setting up the STC. Generally, all methods are similar, but some of them may be more suitable for you, depending on your skills and requirements.
  p Let's choose the most suitable method from the following options:
  ul
    li
      h6 IPFS HTTP API
      p Follow Summa's <a href="https://izihawa.github.io/summa/quick-start/">Quick Start guide</a> to set up your own Summa instance. Pay an attention that you may have to launch Summa within host network:
      pre
        code docker run -v $(pwd)/summa.yaml:/summa.yaml -v $(pwd)/data:/data --network=host izihawa/summa-server:testing serve /summa.yaml
      p Next, we need a database to attach to Summa
      pre
        code
          | summa-cli 0.0.0.0:8082 attach-index nexus_science \
          | '{"remote": {"config": {"method": "GET", "headers_template": {"range": "bytes={start}-{end}", "host": "standard--template--construct-org.ipns.localhost:8080"}, "url_template": "http://localhost:8080/data/{file_name}", "cache_config": {"cache_size": 536870912}}}}'
      p
        | <b>Pros:</b> always up to date
        br
        | <b>Cons:</b> very slow
    li
      h6 File System
      p Follow Summa's <a href="https://izihawa.github.io/summa/quick-start/">Quick Start guide</a> to set up your own Summa instance. Download database:
      pre
        code
          | mkdir -p data/bin/nexus_science
          | ipfs get /ipns/libstc.cc/data --output data/bin/nexus_science --progress
      p Then, attach it to Summa
      pre
        code summa-cli 0.0.0.0:82 attach-index nexus_science '{"file": {}}'
      p
        | <b>Pros:</b> ultra fast
        br
        | <b>Cons:</b> need to maintain updates manually
    li
      h6 Python GECK
      p <a href="https://github.com/nexus-stc/stc/tree/master/geck">GECK</a> contains embedded Summa server that can be utlizied. Install it and then launch serving
      pre
        code geck --ipfs-http-base-url http://127.0.0.1:8080 - serve
  p Now, you have set up Summa with an attached STC index that can be used through the CLI, Python API, or GRPC API in any language.
</template>
<script lang="ts">
import { defineComponent } from 'vue'
export default defineComponent({
  name: 'ReplicateView',
  created () {
    document.title = 'Set Up Your Own Replica - Help - STC'
  }
})
</script>
