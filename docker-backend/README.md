# OKN Map Data

This folder holds the RDF data that powers the OKN Map.
It also holds a Dockerfile that processes these files when deploying the OKN Map.

Individual files represent either Theme 1 graphs or external RDF ontologies referred to by those graphs.
They are intended to be used all together, although in some cases there may be some content overlap between files.

Most of these files are created using the LinkML runtime's RDF generator, based on [schema definitions](https://github.com/frink-okn/schema-gen/tree/main/schema) assembled from Theme 1 graphs or external ontologies.
There are two exceptions, however:

* '_equivalentclasses.ttl' holds skos:exactMatch mappings based on Wikidata ['equivalent class'](https://www.wikidata.org/entity/P1709) and ['exact match'](https://www.wikidata.org/entity/P1709) statements, among others.
* '_manualequivalents.ttl' holds similar mappings to Wikidata entities added after manual inspection of the Theme 1 graph schemas.