#!/bin/bash
# run_queries.sh - Run SPARQL queries against the triple store
#
# This script queries the OKN triple store to extract:
# 1. All classes DEFINED in T1 graphs (schema definitions)
# 2. All classes USED in T1 graphs (from usage statistics)
#
# The results are saved to the analysis directory for further processing.

set -e

# Configuration
SPARQL_ENDPOINT="${SPARQL_ENDPOINT:-http://localhost:8000}"
OUTPUT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFINED_OUTPUT="$OUTPUT_DIR/defined_classes.xml"
USED_OUTPUT="$OUTPUT_DIR/used_classes.xml"

echo "OKN Map - Class Usage Query Script"
echo "===================================="
echo "SPARQL Endpoint: $SPARQL_ENDPOINT"
echo "Output Directory: $OUTPUT_DIR"
echo ""

# Query 1: All defined classes across T1 graphs
echo "Running Query 1: Defined Classes..."
curl -G "$SPARQL_ENDPOINT" --data-urlencode "query=PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?graph ?graphLabel ?class ?classLabel ?classUri WHERE {
  ?graph dct:isPartOf okn:proto-okn ;
         a linkml:SchemaDefinition .

  ?class a linkml:ClassDefinition ;
         skos:inScheme ?graph ;
         linkml:class_uri ?classUri .

  optional { ?graph dct:title ?graphLabel }
  optional { ?class dct:title ?classLabel }
}" 2>/dev/null > "$DEFINED_OUTPUT"

if [ $? -eq 0 ]; then
  echo "✓ Saved to: $DEFINED_OUTPUT"
  DEFINED_COUNT=$(grep -c "<result>" "$DEFINED_OUTPUT" || echo "0")
  echo "  Found $DEFINED_COUNT defined class entries"
else
  echo "✗ Query 1 failed"
  exit 1
fi

echo ""

# Query 2: All used classes across T1 graphs
echo "Running Query 2: Used Classes..."
curl -G "$SPARQL_ENDPOINT" --data-urlencode "query=PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?graph ?graphLabel ?classUri ?count WHERE {
  ?graph dct:isPartOf okn:proto-okn ;
         a linkml:SchemaDefinition .

  ?graph linkml:annotations [
    linkml:tag okns:counts ;
    skos:example/linkml:classes/skos:example [ ?classUri ?s ]
  ] .

  optional { ?graph dct:title ?graphLabel }

  ?s ?p ?count .
  filter(?p = skos:example)
}" 2>/dev/null > "$USED_OUTPUT"

if [ $? -eq 0 ]; then
  echo "✓ Saved to: $USED_OUTPUT"
  USED_COUNT=$(grep -c "<result>" "$USED_OUTPUT" || echo "0")
  echo "  Found $USED_COUNT used class entries"
else
  echo "✗ Query 2 failed"
  exit 1
fi

echo ""
echo "Queries completed successfully!"
echo ""
echo "Next step: Run analyze_class_usage.py to process the results"
