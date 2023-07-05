# Standard Template Construct

Welcome, developer! You've arrived at the repository for STC, 
a reliable search engine offering free access to academic knowledge and works of fictional literature.
STC operates over [IPFS](https://ipfs.tech/), a distributed system that provides robust storage for STC's datasets.

In essence, STC is a search engine coupled with databanks.
These databanks reside on IPFS in a format that allows for searching without necessitating
the download of the entire dataset. The search engine library functions as a standalone server,
an embeddable Python library (requiring no additional software!),
and a WASM-compiled module that can be used in a browser.
Hence, you can open STC in your browser or on your server,
avoiding the use of centralized servers that may lose or censor data.

Several auxiliary projects exist alongside STC to ensure its accessibility to a diverse range of users:

- 🏞 [GECK](/geck) is a Python library and Bash tool for interacting with STC programmatically.
- 🤖 [Cybrex AI](/cybrex) library pairs STC with AI tools such as OpenAI for processing stored data
- 💬 [Telegram Nexus Bot](/tgbot) allows users to access STC via Telegram, one of the most popular messaging platforms.
- 🪐 [Web STC](/web) is a web-based search engine that can be entirely constructed and deployed on IPFS.
