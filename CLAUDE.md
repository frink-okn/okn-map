# OKN Map - Technical Documentation

This document describes the architecture, data model, queries, and setup for the OKN Map project.

## Overview

The OKN Map is a visualization tool for exploring the Prototype Open Knowledge Network (Proto-OKN). It displays a **metagraph** - metadata about knowledge graphs rather than the graphs themselves. Each graph's structure (schema), classes, properties, and relationships to other graphs are visualized interactively.

## Architecture

### Backend: Triple Store
- **Technology**: `rdflib-endpoint` - a Python-based SPARQL server
- **Data Format**: RDF/Turtle (.ttl files)
- **Endpoint**: `http://localhost:8000` (GET requests with query parameter)
- **Total Triples**: ~586,353 triples loaded from all TTL files

### Frontend: Vue.js Web Application
- **Framework**: Vue 3 + Vite
- **Visualization**: Cytoscape.js (graph visualization library)
- **SPARQL Client**: `fetch-sparql-endpoint` (SparqlEndpointFetcher)
- **Dev Server**: `http://localhost:5173/okn-map/`
- **Base Path**: `/okn-map/` (configured in vite.config.ts)

## Data Structure

### TTL Files in docker-backend/

1. **Theme 1 (T1) Graphs** - Individual knowledge graphs from the OKN project:
   - `spoke.ttl` - SPOKE (health/biology)
   - `biobricks-ice.ttl` - BioBricks-ICE
   - `dreamkg.ttl` - DREAM-KG (justice)
   - `nikg.ttl` - Neighborhood Information KG
   - `ruralkg.ttl` - Rural-KG
   - `scales.ttl` - SCALES
   - `securechainkg.ttl` - Secure Chain (manufacturing)
   - `sudokn.ttl` - SUD-OKN
   - And others...

2. **External Ontologies** - Foundational ontologies that T1 graphs depend on:
   - `foaf.ttl` - Friend of a Friend
   - `dc.ttl` - Dublin Core
   - `owl-rdf-rdfs.ttl` - OWL, RDF, RDFS
   - `sdo.ttl` - schema.org
   - And many others...

3. **Equivalence Mappings**:
   - `_equivalentclasses.ttl` - Scraped from Wikidata (P1709/P2888 properties)
   - `_manualequivalents.ttl` - Hand-curated mappings to Wikidata entities

### Schema Structure (LinkML-based)

Each TTL file describes a graph's schema using LinkML vocabulary:

```turtle
# Graph/Schema Definition
okns:spoke a linkml:SchemaDefinition ;
    dct:title "SPOKE" ;
    dct:contributor <mailto:email@example.com> ;
    dct:license "https://creativecommons.org/..." ;
    skos:definition "Description of the graph" ;
    linkml:imports okns:other-graph ;  # Dependencies
    linkml:annotations [ ... ] .       # Usage statistics

# Class Definition
okns:Neo4jDisease a linkml:ClassDefinition ;
    skos:inScheme okns:spoke ;         # Belongs to SPOKE
    linkml:class_uri neo4j:Disease ;   # Actual URI in data
    linkml:slots [ ... ] ;             # Properties/predicates
    dct:title "Disease" .

# Slot/Property Definition
okns:neo4j_name a linkml:SlotDefinition ;
    linkml:domain_of okns:Neo4jDisease ;
    linkml:range okns:string ;
    linkml:slot_uri neo4j:name .
```

### Usage Statistics (Counts)

Embedded in the schema annotations:

```turtle
linkml:annotations [
    linkml:tag okns:counts ;
    skos:example [
        linkml:classes [
            skos:example [
                neo4j:Disease [
                    skos:example "153323" ;  # Count of instances
                    linkml:tag neo4j:Disease
                ]
            ]
        ]
    ]
] .
```

## Key Prefixes

```sparql
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
```

## SPARQL Queries

### Query 1: getDefinedClasses
**Purpose**: Show classes defined within a graph (internal classes)

**When**: Right-click graph → "Show defined classes"

```sparql
SELECT distinct ?class ?classLabel WHERE {
  ?class a linkml:ClassDefinition ;
         skos:inScheme okns:spoke ;           # Filter to this graph
         linkml:class_uri ?classuri .
  # Only show classes that have actual usage/instances
  [] linkml:tag okns:counts ;
     skos:example [ linkml:classes [ skos:example [ ?classuri [] ] ] ]
  optional { ?class dct:title ?classLabel }
} limit 10
```

**Result for SPOKE**: Returns 6 classes (Neo4jDisease, Neo4jCompound, Neo4jOrganism, Neo4jEnvironment, Neo4jLocation, Neo4jSDoH)

### Query 2: getAllUsedClasses
**Purpose**: Show which classes appear in a graph's usage statistics

**When**: Right-click graph → "Show used classes"

```sparql
SELECT ?graph ?graphLabel ?class ?classLabel ?count WHERE {
  # Navigate to the counts section
  okns:spoke linkml:annotations [
    linkml:tag okns:counts ;
    skos:example/linkml:classes/skos:example [ ?class_ ?s ]
  ] .

  # Find which graph defines each class
  ?class a linkml:ClassDefinition ;
         linkml:class_uri ?class_ ;
         skos:inScheme ?graph .

  optional { ?graph dct:title ?graphLabel }
  optional { ?class dct:title ?classLabel }

  # Extract the count
  ?s ?p ?count .
  filter(?p = skos:example)
} limit 10
```

**Behavior**:
- Returns all classes found in usage counts (both internal and external)
- JavaScript filters out internal classes (where `?graph == okns:spoke`)
- Only draws edges for external classes

**Note**: This query can be confusing - it returns both internal and external classes, but the visualization only shows relationships to external ones.

### Query 3: getEquivalentClasses (Single Class)
**Purpose**: Find semantically equivalent classes for ONE specific class

**When**: Right-click on a class node (red dot) → "Show equivalent classes"

```sparql
SELECT ?class ?classLabel ?graph ?graphLabel WHERE {
  # Two paths to find equivalences:

  # Path A: Direct SKOS mappings
  { okns:Neo4jDisease skos:exactMatch|skos:closeMatch|skos:broadMatch ?class_ }

  union

  # Path B: Transitive through Wikidata
  {
    okns:Neo4jDisease linkml:class_uri ?c1_ .
    # ^skos:exactMatch means "reverse direction" - find things that point TO this URI
    ?c1_ ^skos:exactMatch/skos:exactMatch ?class_
  }

  # Find which graph defines the equivalent class
  ?class a linkml:ClassDefinition ;
         linkml:class_uri ?class_ ;
         skos:inScheme ?graph .

  optional { ?class dct:title ?classLabel }
  optional { ?graph dct:title ?graphLabel }
} limit 10
```

**Path B Explanation** (Transitive via Wikidata):
```
okns:Neo4jDisease → neo4j:Disease ← wd:Q12136 → mondo:Disease
                    (class URI)    (Wikidata)   (MONDO URI)
```

The `^` operator reverses the direction, so:
- `A ^skos:exactMatch` means "find things that have `skos:exactMatch A`"
- This allows traversing through Wikidata entities that link multiple ontologies

### Query 3b: getAllEquivalentClasses (All Classes in Graph)
**Purpose**: Find equivalences for ALL classes in a graph at once

**When**: Right-click graph → "Show equivalent classes"

```sparql
SELECT ?c1 ?c1Label ?class ?classLabel ?graph ?graphLabel WHERE {
  # Find all classes in this graph
  ?c1 skos:inScheme okns:spoke .

  # Same two paths as Query 3
  { ?c1 skos:exactMatch|skos:closeMatch|skos:broadMatch ?class_ }
  union
  { ?c1 linkml:class_uri ?c1_ .
    ?c1_ ^skos:exactMatch/skos:exactMatch ?class_ }

  # Find the external graph (filter out self)
  ?class linkml:class_uri ?class_ ;
         skos:inScheme ?graph .
  filter(?graph != okns:spoke)

  optional { ?class dct:title ?classLabel }
  optional { ?graph dct:title ?graphLabel }
} limit 10
```

**Graphs with equivalences**:
- schema.org (sdo): 350 equivalences
- SPOKE: 14 equivalences
- NIKG, Wildlife-KN: 8 each
- DREAM-KG: 0 (no equivalences)

### Query 4: getGraphImports
**Purpose**: Show dependency relationships between graphs

**When**: Right-click graph → "Show graph dependencies"

```sparql
SELECT ?s ?sLabel ?o ?oLabel WHERE {
  VALUES ?s { okns:biobricks-ice }
  ?s linkml:imports ?o .
  # Commented out: minus { ?s linkml:imports ?p . ?p linkml:imports+ ?o }
  # (Would filter to direct imports only, excluding transitive)
  optional { ?s dct:title ?sLabel }
  optional { ?o dct:title ?oLabel }
} limit 100
```

**Result**: Green arrows showing import relationships

## Visualization Behavior

### Edge Types (Colors)
- **Green arrows** (`import`): Graph A imports/depends on Graph B
- **Blue bidirectional arrows** (`equivalent`): Classes are semantically equivalent
- **Orange arrows with counts** (`classuse`): Graph A uses N instances of a class from Graph B

### Node Types
- **Large rectangles with icons**: Use case categories (Biology & Health, Environment, Justice, Tech & Manufacturing)
- **Yellow/green/blue/red dots**: T1 graphs (colored by use case)
- **Gray dots**: External ontologies
- **Red dots inside graphs**: Class definitions

### Initial State (Hardcoded)
The initial visualization is hardcoded in `App.vue` lines 34-70:
- 4 use case category nodes (fixed positions)
- Dictionary mapping each use case to its T1 graphs
- T1 graphs appear when you click on a use case category

**TODO comments** indicate this should be moved to configuration or queried from the triple store.

## Running the System

### Backend (Triple Store)

**Option 1: Docker**
```bash
cd docker-backend
docker build -t okn-triplestore .
docker run -p 8000:8000 okn-triplestore
```

**Option 2: Direct Python**
```bash
cd docker-backend
pip install rdflib-endpoint[web] rdflib-endpoint[cli]
rdflib-endpoint serve --host 0.0.0.0 --port 8000 *.ttl
```

**Test the endpoint**:
```bash
curl -G http://localhost:8000 \
  --data-urlencode "query=SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 5"
```

### Frontend (Vue App)

**Development mode** (recommended):
```bash
cd /Users/bizon/Projects/OKN/okn-map
npm install
npm run dev
```

Access at: **`http://localhost:5173/okn-map/`** (note the `/okn-map/` path)

**Docker mode** (has path issues currently):
```bash
docker build -f docker-frontend/Dockerfile -t okn-frontend .
docker run -p 8080:8080 \
  -e API_URL=http://localhost:8000 \
  -e PUBLIC_URL=http://localhost:8080 \
  okn-frontend
```

**Issue**: Docker build expects assets at `/okn-map/` but serves from root. Use dev mode instead.

### Configuration

The frontend tries to load `config.json` to get the SPARQL endpoint URL:
```javascript
// App.vue lines 16-24
const oknSparqlEndpoint = ref("http://localhost:8000")
onMounted(async () => {
  try {
    let response = await fetch("/okn-map/config.json");
    const config = await response.json();
    oknSparqlEndpoint.value = config.sparqlEndpoint;
  } catch (e) {
    // Falls back to localhost:8000
  }
})
```

## Data Generation

### For Individual Graphs

1. Generate LinkML schema (in separate `schema-gen` repo):
   ```bash
   # See https://github.com/frink-okn/schema-gen
   ```

2. Convert schema to RDF:
   ```bash
   python3 src/rdfgen-frink.py your-graph.yaml > docker-backend/your-graph.ttl
   ```

### For Equivalence Files

- **`_manualequivalents.ttl`**: Hand-curated file mapping Wikidata entities to graph URIs
- **`_equivalentclasses.ttl`**: Generated by querying Wikidata (script not published)

Both files provide `skos:exactMatch` statements that link classes across graphs via Wikidata as a bridge.

## Key Files

- `src/App.vue` - Main application component with all queries and visualization logic
- `src/prefixes.js` - RDF prefix definitions for shrinking/expanding URIs
- `vite.config.ts` - Build configuration (note `base: "/okn-map/"`)
- `docker-backend/Dockerfile` - Backend triple store container
- `docker-frontend/Dockerfile` - Frontend nginx container
- `docker-backend/*.ttl` - All RDF data files

## Known Issues / TODOs

1. **Hardcoded T1 graphs**: Should be queried from triple store (App.vue:44)
2. **Docker frontend path issues**: Assets expected at `/okn-map/` but served from root
3. **Empty results handling**: UI appears to "hang" when queries return no results (e.g., DREAM-KG equivalences)
4. **Query 2 naming**: `getAllUsedClasses` is misleading - it returns all classes but only visualizes external ones

## Tips for Development

1. **Use dev mode** (`npm run dev`) - much easier than Docker for frontend development
2. **Check browser console** for SPARQL query debugging (queries are logged)
3. **Test queries directly** via curl against `http://localhost:8000` before debugging UI
4. **Graphs with best test data**:
   - SPOKE: Has defined classes, used classes, and equivalences
   - BioBricks-ICE: Has imports and external class usage
   - DREAM-KG: Has classes but NO equivalences (good for testing empty results)

## For Creating a Fork/Variant

To create a parallel system with subset data and different UI:

1. **Keep the same stack**:
   - Backend: rdflib-endpoint with TTL files
   - Frontend: Vue 3 + Vite + Cytoscape.js
   - Container setup similar to current

2. **Data subset**:
   - Copy relevant TTL files to your fork's `docker-backend/`
   - Optionally transform/filter the triples
   - Keep the LinkML schema structure or adapt as needed

3. **UI modifications**:
   - Fork `src/App.vue` and modify queries/visualization
   - Adjust `vite.config.ts` base path if needed
   - Update hardcoded graph lists or make them query-based

4. **Docker setup**:
   - Same Dockerfile pattern for backend (rdflib-endpoint)
   - Frontend Dockerfile may need path fixes (or use dev mode)

The architecture is fairly modular - backend just serves SPARQL, frontend just queries and visualizes. You can swap out either side independently.
