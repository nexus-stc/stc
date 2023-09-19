# Cybrex AI

Cybrex AI integrates several strategies to use AI for facilitating navigation through science. Shortly, Cybrex accept your query, retrieve scholarly publications and books from STC and answer your query using AI and collected documents.

More technical description:
- IPFS is utilized to access the Standard Template Construct (STC).
- STC provides the raw documents for Cybrex.
- Embedding Model constructs embeddings for these documents and Cybrex stores these embeddings in the vector database.
- These embeddings are then used to retrieve relevant documents and then they are sent to LLM for Q&A and summarization.

## Install

You should have [installed IPFS](http://standard-template-construct.org/#/help/install-ipfs)

Then, you should install cybrex package
```bash
pip install cybrex
```

and launch qdrant database for storing vectors:

```bash 
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant 
```

Upon its initial launch, `cybrex` will create a `~/.cybrex` directory containing a `config.yaml` file and a `chroma` directory.
You can edit the config file to point to different IPFS addresses.

## Usage

**Attention!** STC does not contain every book or publication in the world. We are constantly increasing coverage but there is still a lot to do.
STC contains metadata for the most of the items, but `links` or `content` fields may be absent.

```console
# (Optional) Launch Summa search engine, then you will not have to wait bootstrapping every time.
# It will take a time!
# If you decided to launch it, switch to another Terminal window
geck --ipfs-http-base-url 127.0.0.1:8080 - serve
```

Now we should initialize Cybrex and choose which models will be used:

``` console
cybrex - write-config --force
# or if you want to use OpenAI model, export keys and you should set appropriate models in config:
export OPENAI_API_KEY=...
cybrex - write-config -l openai --force

# Summarize a document
cybrex - sum-doc doi:10.1155/2022/7138756

Document: doi:10.1155/2022/7138756
Summarization: Resveratrol is a natural compound found in various plants and has been studied for 
its anti-inflammatory and antiviral properties. Resveratrol has been shown to regulate miR-223-3p/NLRP3 
pathways, inhibit downstream caspase-1 activation, reduce the expression of chemokines, and decrease 
the levels of calcium strength, pro-inflammatory cytokines, and MDA in an acute bacterial meningitis model. 
It can also regulate the PI3K/Akt/mTOR signaling pathway, reduce NF-κB/p65 and pro-inflammatory cytokines, 
and increase nitric oxide, sialic acid, gastric tissue, and vitamin C concentrations. Resveratrol has been 
found to inhibit viral replication and have antiviral activity against Zika Virus, Pseudorabies virus, 
and HSV-1. The exact mechanisms of action of resveratrol are still not fully understood, but it is believed 
to activate the host's immune defences, affect the TLRs/NF-κB signalling pathway, and directly inhibit 
viral gene expression.

# Question a document
cybrex - chat-doc doi:10.1155/2022/7138756 \
  --query "What is the antivirus effect of resveratrol?"

Q: What is the antivirus effect of resveratrol?
A: Resveratrol has been found to have antiviral effects, primarily through its ability to inhibit viral
entry and replication. It has been reported to inhibit the replication of multiple viruses, including
human immunodeficiency virus (HIV), herpes simplex virus (HSV), hepatitis C virus (HCV), and
Zika virus (ZIKV). Resveratrol appears to block the activities of the TIR-domain-containing
adapter-inducing interferon-β (TRIF) complex, suggesting that resveratrol would also inhibit NF-κB
transcription induced by TRIF. Additionally, it has been reported to reduce the activity of respiratory
syncytial virus (RSV) and to stimulate the secretion of higher levels of TNF-α, promoting cell death
and RSV clearance.

# Question enitre science
cybrex - chat-sci "What is the antivirus effect of resveratrol?" --n-chunks 4 --n-documents 10

Q: What is the antivirus effect of resveratrol?
A: Resveratrol has been found to possess antiviral activity against a variety of viruses, including herpes simplex virus, human immunodeficiency virus, and hepatitis C virus. It has been shown to inhibit the replication of several viruses, including HIV, herpes simplex virus, and influenza virus, and to regulate TLR3 expression, thus affecting the recruitment of downstream related factors and finally affecting the regulation process of related signal pathways. It has also been studied for its antiviral activity against Reoviridae, and for its potential to inhibit Zika virus cytopathy effect. It has been active against Epstein virus, rotavirus, and vesicular stomatitis virus, and has been reported to alleviate virus-induced reproductive failure and to promote RSV clearance in the body more quickly.

```
