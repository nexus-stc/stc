# GECK (Garden of Eden Creation Kit)

GECK is a Python library and Bash tool for deploy andaccess STC - the large corpus of scholarly texts.
GECK includes embedded search engine [Summa](https://github.com/izihawa/summa), helps to feed it with a prepared IPFS-based database of scholarly texts, do search queries over the database and iterate over all documents if you need.

## Install

You should have [installed IPFS](http://standard-template-construct.org/#/help/install-ipfs)
Pre-built wheels available for Python 3.8, 3.9, 3.10 and 3.11

```bash
pip install stc-geck
```

## Usage

**Attention!** STC does not contain every book or publication in the world. We are constantly increasing coverage but there is still a lot to do.
STC contains metadata for the most of the items, but `links` or `content` fields may be absent.

### CLI

```console
# (Optional) Launch standalone Summa search engine, then you will not have to wait bootstrapping every time.
# It will take a time! Wait until the text `Serving on ...` appears
# If you decided to launch it, switch to another Terminal window
ultranymous@nevermore:~ geck - serve
INFO: Serving on 127.0.0.1:10082

# Iterate over all stored documents
ultranymous@nevermore:~ geck - documents
INFO: Setting up indices...
{"authors":[{"family":"Manresa Presasa","given":"JM","sequence":"first"},{"family":"Rebull Fatsinib","given":"J","sequence":"additional"},{"family":"Miravalls Figuerolac","given":"M","sequence":"additional"},{"family":"Caballol Angelatsd","given":"R","sequence":"additional"},{"family":"Minué Magañae","given":"P","sequence":"additional"},{"family":"Juan Franquetf","given":"R","sequence":"additional"}],"ctr":0.1,"custom_score":1.0,"doi":"10.1157/13053458","issued_at":7376313600,"language":"es","metadata":{"container_title":"Atención Primaria","first_page":435,"issns":["0212-6567","1578-1275"],"issue":"7","last_page":436,"publisher":"Elsevier BV","volume":"32"},"page_rank":0.16246586,"referenced_by_count":5,"tags":["Family Practice","General Medicine"],"title":"La espirometría en el diagnóstico de la enfermedad pulmonar obstructiva crónica en atención primaria","type":"journal-article","updated_at":1687530735}
{"authors":[{"family":"Yanes Baonza","given":"M","sequence":"first"},{"family":"Ferrer García-Borrás","given":"JM","sequence":"additional"},{"family":"Cabrera Majada","given":"A","sequence":"additional"},{"family":"Sánchez González","given":"R","sequence":"additional"}],"ctr":0.1,"custom_score":1.0,"doi":"10.1157/13053456","issued_at":7376313600,"language":"es","metadata":{"container_title":"Atención Primaria","first_page":438,"issns":["0212-6567","1578-1275"],"issue":"7","last_page":438,"publisher":"Elsevier BV","volume":"32"},"page_rank":0.15,"referenced_by_count":0,"tags":["Family Practice","General Medicine"],"title":"Sonambulismo asociado con zolpidem","type":"journal-article","updated_at":1687530735}
{"authors":[{"family":"Fernández Fernández","given":"I","sequence":"first"}],"ctr":0.1,"custom_score":1.0,"doi":"10.1157/13053452","issued_at":7376313600,"language":"es","metadata":{"container_title":"Atención Primaria","first_page":440,"issns":["0212-6567","1578-1275"],"issue":"7","last_page":440,"publisher":"Elsevier BV","volume":"32"},"page_rank":0.15,"referenced_by_count":0,"tags":["Family Practice","General Medicine"],"title":"Respuesta de la autora","type":"journal-article","updated_at":1687530735}
{"authors":[{"family":"Nieto Blanco","given":"E","sequence":"first"},{"family":"Camacho Pérez","given":"J","sequence":"additional"},{"family":"Dávila Álvarez","given":"V","sequence":"additional"},{"family":"Ledo García","given":"MP","sequence":"additional"},{"family":"Moriano Bejar","given":"P","sequence":"additional"},{"family":"Pérez Lorente","given":"M","sequence":"additional"},{"family":"Serrano Molina","given":"L","sequence":"additional"},{"family":"Fonseca Redondo","given":"B","sequence":"additional"}],"ctr":0.1,"custom_score":1.0,"doi":"10.1157/13053465","issued_at":7376313600,"language":"es","metadata":{"container_title":"Atención Primaria","first_page":410,"issns":["0212-6567","1578-1275"],"issue":"7","last_page":414,"publisher":"Elsevier BV","volume":"32"},"page_rank":0.18173838,"referenced_by_count":5,"tags":["Family Practice","General Medicine"],"title":"Epidemiología e impacto de la incontinencia urinaria en mujeres de 40 a 65 años de edad en un área sanitaria de Madrid","type":"journal-article","updated_at":1687530735}
{"authors":[{"family":"Burillo-Putze","given":"G","sequence":"first"},{"family":"Osuna Peña","given":"JM","sequence":"additional"},{"family":"García Marín","given":"V","sequence":"additional"},{"family":"García Marín","given":"N","sequence":"additional"}],"ctr":0.1,"custom_score":1.0,"doi":"10.1157/13053455","issued_at":7376313600,"language":"es","metadata":{"container_title":"Atención Primaria","first_page":438,"issns":["0212-6567","1578-1275"],"issue":"7","last_page":438,"publisher":"Elsevier BV","volume":"32"},"page_rank":0.15,"referenced_by_count":0,"tags":["Family Practice","General Medicine"],"title":"Síndrome de latigazo cervical y pruebas radiológicas","type":"journal-article","updated_at":1687530735}
{"authors":[{"family":"Castiella","given":"S","sequence":"first"},{"family":"López Vázquez","given":"MA","sequence":"additional"}],"ctr":0.1,"custom_score":1.0,"doi":"10.1157/13053454","issued_at":7376313600,"language":"es","metadata":{"container_title":"Atención Primaria","first_page":439,"issns":["0212-6567","1578-1275"],"issue":"7","last_page":439,"publisher":"Elsevier BV","volume":"32"},"page_rank":0.15,"referenced_by_count":0,"tags":["Family Practice","General Medicine"],"title":"Respuesta de los autores","type":"journal-article","updated_at":1687530735}
{"authors":[{"family":"Carmona Ibáñez","given":"G","sequence":"first"},{"family":"Guevara Serrano","given":"J","sequence":"additional"}],"ctr":0.1,"custom_score":1.0,"doi":"10.1157/13053464","issued_at":7376313600,"language":"es","metadata":{"container_title":"Atención Primaria","first_page":415,"issns":["0212-6567","1578-1275"],"issue":"7","last_page":419,"publisher":"Elsevier BV","volume":"32"},"page_rank":0.15,"referenced_by_count":0,"tags":["Family Practice","General Medicine"],"title":"Estudio de la marca en la prescripción de genéricos en 6 centros de salud durante el año 2001","type":"journal-article","updated_at":1687530735}

# Do a match search by field
ultranymous@nevermore:~ geck - search doi:10.3384/ecp1392a41
INFO: Setting up indices...
INFO: Searching doi:10.3384/ecp1392a41...
{"abstract": "In recent years, water hydraulics has been getting more <...> "type": "proceedings-article", "updated_at": 1687530737}

# Do a match search by word. In the example below documents are cut for displaying reason
ultranymous@nevermore:~ geck - search hemoglobin --limit 3
INFO: Setting up indices...
INFO: Searching hemoglobin...
{"abstract": "Abstract\nWe exa <...>
{"abstract": "Abstract\nUsing a <...>
{"abstract": "Regional cerebral <...>
```

You can add `--debug` flag after `geck` to enable debugging output.

### Python

```python
import argparse
import asyncio

from stc_geck.advices import format_document
from stc_geck.client import StcGeck

DEFAULT_LIMIT = 5


async def main(limit: int):
    geck = StcGeck(
        ipfs_http_base_url='http://127.0.0.1:8080',
        timeout=300,
    )

    # Connects to IPFS and instantiate configured indices for searching
    # It will take a time depending on your IPFS performance
    await geck.start()

    # GECK encapsulates Python client to Summa.
    # It can be either external stand-alone server or embed server,
    # but details are hidden behind `SummaClient` interface.
    summa_client = geck.get_summa_client()

    # Match search returns top-5 documents which contain `additive manufacturing` in their title, abstract or content.
    documents = await summa_client.search_documents({
        "index_alias": "nexus_science",
        "query": {
            "match": {
                "value": "additive manufacturing",
                "query_parser_config": {"default_fields": ["abstract", "title", "content"]}
            }
        },
        "collectors": [{"top_docs": {"limit": limit}}],
        "is_fieldnorms_scoring_enabled": False,
    })

    for document in documents:
        print(format_document(document) + '\n')

    await geck.stop()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--limit', type=int, default=DEFAULT_LIMIT)
    args = argparser.parse_args()

    asyncio.run(main(args.limit))
```

More example for Python can be found in [examples directory](/geck/examples/search-stc.ipynb)
