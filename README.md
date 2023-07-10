# Standard Template Construct

Welcome, reader! 
You've arrived at the repository for [STC](http://standard-template-construct.org), a search engine offering free access to academic knowledge and works of fictional literature.

![](/misc/logo.svg)

[Repository IPFS mirror](http://repo.standard-template-construct.org) | 
[Telegram](https://t.me/+3UReK0DgPeBhOWQy) | 
[Twitter](https://twitter.com/the_superpirate) | 
[Mastodon](https://kolektiva.social/@the_superpirate)

### Web STC 

[Web STC](/web) is a web-based search engine that can be entirely constructed and deployed on IPFS

### STC Hub

STC Hub is plain API for accessing scholarly publications through `kubo` command line tools or even through HTTP:

```bash
ipfs get /ipns/hub.standard-template-construct.org/{urlencode(doi)}.pdf
```
or
```bash
# Take a note on double URL encoding, effectively it means you should replace `/` with `%252F`
curl "http://127.0.0.1:8080/ipns/hub.standard-template-construct.org/{urlencode(urlencode(doi))}" \
--output file.pdf
```

### GECK

[GECK](/geck) is a Python library and Bash tool for interacting with STC programmatically

### Cybrex AI

[Cybrex AI](/cybrex) library pairs STC with AI tools such as OpenAI for processing stored data

### Telegram Bots

[Telegram Nexus Bot](/tgbot) allows users to access STC via Telegram, one of the most popular messaging platforms.

## Details
STC operates over [IPFS](https://ipfs.tech/), a distributed system that provides robust storage for STC's datasets.

In essence, STC is a search engine coupled with databanks.
These databanks reside on IPFS in a format that allows for searching without necessitating
the download of the entire dataset. The search engine library functions as a standalone server,
an embeddable Python library (requiring no additional software!),
and a WASM-compiled module that can be used in a browser.
Hence, you can open STC in your browser or on your server,
avoiding the use of centralized servers that may lose or censor data.
