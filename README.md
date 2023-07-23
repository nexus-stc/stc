# Standard Template Construct

Welcome, developer!
You've arrived at the repository for [STC](http://standard-template-construct.org), a search engine offering free access to academic knowledge and works of fictional literature.

![](/web/public/favicon.svg)

STC operates over [IPFS](https://ipfs.tech/), a distributed system that provides robust storage for STC's datasets.

In essence, STC is a search engine coupled with databanks.
These databanks reside on IPFS in a format that allows for searching without necessitating
the download of the entire dataset. The search engine library functions as a standalone server,
an embeddable Python library (requiring no additional software!),
and a WASM-compiled module that can be used in a browser.
Hence, you can open STC in your browser or on your server,
avoiding the use of centralized servers that may lose or censor data.

[Help Center](http://standard-template-construct.org/#/help)

## Components

### Cybrex AI

[Cybrex AI](/cybrex) library pairs STC with AI tools such as OpenAI for processing stored data

### GECK

[GECK](/geck) is a Python library and Bash tool for interacting with STC programmatically

### STC Hub API

[STC Hub API](http://standard-template-construct.org/#/help/stc-hub-api) is plain API for accessing scholarly publications through `kubo` command line tools or even through HTTP.

### Telegram Bots

[Telegram Nexus Bot](/tgbot) allows users to access STC via Telegram, one of the most popular messaging platforms.

### Web STC 

[Web STC](/web) is a web-based search engine that can be entirely constructed and deployed on IPFS

## Roadmap

| Part                | Task                                    | Description                                                                                                                                                                                                                           |
|---------------------|-----------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Library Stewardship |                                         |                                                                                                                                                                                                                                       | 
|                     | Assimilation of LibGen corpus           | Transition DOI-stamped items to `nexus_science`, transfer fiction to `nexus_free`                                                                                                                                                     |
|                     | Assimilation of scimag corpus           | Significant task of transferring scimag corpus to IPFS                                                                                                                                                                                |
|                     | Structured content                      | Enhance GROBID extraction (headers + content) and store content in structured_content JSON column. Extract entities for cross-linking in Web STC                                                                                      |
| Web STC             |                                         |                                                                                                                                                                                                                                       |
|                     | UX improvement                          | STC often requires loading of large data chunks, currently reflected only by a spinner. The UX needs improvement. Following structured content implementation, we can highlight headers and generate cross-links in abstracts/content |
|                     | Enhancing availability                  | Further testing needed on diverse devices and networks                                                                                                                                                                                |
|                     | Bookshelf                               | STC has all tools for generating bookshelves that may offer users high-quality suggestions on read.                                                                                                                                   |
| Cybrex AI           |                                         |                                                                                                                                                                                                                                       |
|                     | First-class support of local LLM        | Extensive testing of prompts with documents is required to identify the smallest model capable of efficiently executing QA and summarization tasks. Most 13-15B models are currently failing (quantized, on CPU)                      |
|                     | Building an embeddings dataset          | The goal is to build a comprehensive dataset with DOIs and document embeddings. Currently, the Instructor XL model appears most promising, but further testing is necessary                                                           |
|                     | Refining and fixing metadata            | Areas for improvement include: detected language, tags, keywords, automated abstracts, Dewey classification                                                                                                                           |
|                     | Build QA on local LLM                   | Such a system should be independently operable and also accessible via Telegram.                                                                                                                                                      |
|                     | Fine-tuning LLMs on STC                 |                                                                                                                                                                                                                                       |
| Distribution        |                                         |                                                                                                                                                                                                                                       |
|                     | Building STC Box                        | Develop and maintain a definitive guide and scripts for replicating and launching STC on compact devices like PI computers or TV Boxes                                                                                                |
|                     | Global replication                      | The goal is to replicate STC (including the search database and papers) a minimum of 100 times across at least 30 countries                                                                                                           |
|                     | Establishing Frontier Outposts          | Investigate strategies to replicate STC on an orbiting satellite or another planet in the solar system (Mars or Europa preferred)                                                                                                     |
| Communities         |                                         |                                                                                                                                                                                                                                       |
|                     | Forming Science Communities on Telegram | Initiate the first version of Telegram-based forums focusing on specific scientific topics                                                                                                                                            |
|                     | Addressing Copyright Issues             | Organize more activities aimed at challenging the copyright laws for scholarly and educational writings                                                                                                                               |
