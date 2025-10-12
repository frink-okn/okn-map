# OKN Map

This is the concept map for the Prototype Open Knowledge Network (Proto-OKN).

It displays relationships between Theme 1 graphs, external ontologies on which those graphs depend, and the classes and predicates defined and used in all of them. The relationships are taken from underlying Turtle files generated from LinkML schemas.

## Data generation

To produce the data found in `docker-backend`, schemas must first be generated [as described in the 'schema-gen' repository](https://github.com/frink-okn/schema-gen).

Once a schema `your-graph.yaml` has been produced, then the following command (run in the same directory as the 'schema-gen' repository) will produce an RDF file using the [Turtle](https://www.w3.org/TR/turtle/) syntax:

```
python3 src/rdfgen-frink.py your-graph.yaml >/path/to/docker-backend/your-graph.ttl
```

(Make sure that the dependencies listed in that repository have been installed first!)

## Map deployment

The OKN Map itself is deployed in two parts:

* a frontend built with Vue 3 and Vite (and, in principle, TypeScript) running on top of an nginx server and Node.js runtime; and
* a backend that uses the ['rdflib-endpoint'](https://github.com/vemonet/rdflib-endpoint) Python library as a simple RDF triple-store and SPARQL endpoint.

The Dockerfiles in `docker-backend` and `docker-frontend` should suffice for an arbitrary deployment elsewhere, although the content of `helm` may be adapted from its current contents specific to the deployment at [frink.apps.renci.org](https://frink.apps.renci.org/okn-map/).

## RDF Metagraph Description

This section describes the contents and relationships used by the RDF version of the metagraph.

### Component files

The underlying RDF files used with the OKN Map are as follows:

* External ontologies, generated from [schemas in the 'schema-gen' repository](https://github.com/frink-okn/schema-gen/tree/main/schema).
* Theme 1 graphs, generated from [schemas in the 'graph-descriptions' repository](https://github.com/frink-okn/graph-descriptions).
* IRI equivalences based on ['equivalent class'](https://www.wikidata.org/wiki/Property:P1709) and ['exact match'](https://www.wikidata.org/wiki/Property:P2888) statements in Wikidata, in `_equivalentclasses.ttl`.
* Manually-added equivalences between Theme 1 graph classes/predicates and Wikidata entities, in `_manualequivalents.ttl`.
* Proto-OKN project definition and graph membership relationships, in `proto-okn-project.ttl`.

### Prefixes

The RDF prefixes used in the remainder of this document are as follows:

| Prefix | Definition |
| --- | --- |
| dcterms: | http://purl.org/dc/terms/ |
| foaf: | http://xmlns.com/foaf/0.1/ |
| linkml: | https://w3id.org/linkml/ |
| okn: | http://purl.org/okn/ |
| okns: | http://purl.org/okn/schema/ |
| pav: | http://purl.org/pav/ |
| skos: | http://www.w3.org/2004/02/skos/core# |

### List of predicates

| Predicate | Relationship | Notes |
| --- | --- | --- |
| dcterms:title     | Name of entity | |
| dcterms:license   | License of schema | |
| dcterms:source    | Source document of schema | |
| dcterms:isPartOf  | Graph is part of project | Used to link Theme 1 graphs to the Proto-OKN project |
| pav:createdOn     | Date schema created | |
| pav:lastUpdatedOn | Date schema last updated | |
| pav:version       | Version ID of schema | |
| skos:definition   | Description of entity | |
| linkml:id         | Identifier of entity | |
| linkml:classes    | Class defined in this schema | |
| linkml:slots      | Slot defined in this schema | |
| linkml:types      | Type defined in this schema | |
| linkml:imports    | Schema that this schema imports | |

### List of classes

| Class | Description | Notes |
| --- | --- | --- |
| linkml:SchemaDefinition | A LinkML schema/graph definition | Used for Theme 1 graphs and external ontologies |
| foaf:Project | A collaborative project | Used to represent the Proto-OKN project (okn:proto-okn) |
