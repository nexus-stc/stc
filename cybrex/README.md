# Cybrex AI

## Install

```bash
pip install cybrex
```

## Usage

```bash
# Summarize document
OPENAI_API_KEY=... cybrex sum-doc --doi 10.1155/2022/7138756

# Question a document
OPENAI_API_KEY=... python3 cybrex chat-doc --doi 10.1155/2022/7138756 \
  --question "What is the antivirus effect of resveratrol?"
```
