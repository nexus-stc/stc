# GECK (Garden of Eden Creation Kit)

## Install

```bash
pip install stc-geck
```

## Usage

```bash
# Iterate over all stored documents
geck --ipfs-http-base-url 127.0.0.1:8080 - documents

# Do a match search by field
geck --ipfs-http-base-url 127.0.0.1:8080 - search doi:10.3384/ecp1392a41
# Do a match search by word
geck --ipfs-http-base-url 127.0.0.1:8080 - search hemoglobin --limit 10
```
