# Cybrex AI

Cybrex AI integrates several strategies to boost the role of AI in science:

- IPFS is utilized to access the Standard Template Construct (STC).
- STC provides the raw documents for Cybrex.
- OpenAI constructs embeddings for these documents and Cybrex stores these embeddings locally in the Chroma database.
- These embeddings are then used to filter relevant documents before they are sent to OpenAI for Q&A and summarization.

## Install

```bash
pip install cybrex
```

Upon its initial launch, `cybrex` will create a `~/.cybrex` directory containing a `config.yaml` file and a `chroma` directory.
You can edit the config file to point to different IPFS addresses.

## Usage

```bash
# Summarize a document
OPENAI_API_KEY=... cybrex sum-doc --doi 10.1155/2022/7138756

# Question a document
OPENAI_API_KEY=... python3 cybrex chat-doc --doi 10.1155/2022/7138756 \
  --question "What is the antivirus effect of resveratrol?"
```
