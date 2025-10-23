#!/usr/bin/env python3
"""
Generate precomputed equivalence relationships between OKN graphs.

This script queries the triple store to find all used classes across T1 graphs,
then builds equivalence groups based on:
1. Shared classes (same class used in multiple graphs)
2. Direct SKOS relationships (exactMatch, closeMatch, broadMatch)
3. Indirect Wikidata relationships (classes linked via Wikidata entities)

Output: _precomputed_equivalences.ttl file for the triple store

Usage:
  python3 generate_equivalences.py [--endpoint URL] [--output FILE]
"""

import argparse
import hashlib
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime


class UnionFind:
    """Union-Find data structure for building equivalence classes."""

    def __init__(self):
        self.parent = {}

    def add(self, x):
        if x not in self.parent:
            self.parent[x] = x

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        self.parent[self.find(x)] = self.find(y)

    def get_groups(self):
        """Return sets of elements grouped by their root."""
        groups = defaultdict(set)
        for x in self.parent:
            groups[self.find(x)].add(x)
        return [g for g in groups.values() if len(g) > 1]


def query_sparql(endpoint, query):
    """Execute SPARQL query and return parsed results."""
    params = urllib.parse.urlencode({'query': query})
    url = f"{endpoint}?{params}"

    try:
        with urllib.request.urlopen(url) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"Error querying SPARQL endpoint: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse XML results
    root = ET.fromstring(xml_data)
    ns = {'sparql': 'http://www.w3.org/2005/sparql-results#'}

    results = []
    for result in root.findall('.//sparql:result', ns):
        row = {}
        for binding in result.findall('sparql:binding', ns):
            name = binding.get('name')
            uri_elem = binding.find('sparql:uri', ns)
            literal_elem = binding.find('sparql:literal', ns)

            if uri_elem is not None:
                row[name] = uri_elem.text
            elif literal_elem is not None:
                row[name] = literal_elem.text
        results.append(row)

    return results


def get_used_classes(endpoint):
    """Query all used classes across T1 graphs."""
    query = """
    PREFIX dct: <http://purl.org/dc/terms/>
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
    }
    """

    print("Querying used classes...")
    results = query_sparql(endpoint, query)

    # Build data structure: {graph_uri: {class_uri: count}}
    used_by_graph = defaultdict(dict)
    graph_labels = {}

    for row in results:
        graph_uri = row['graph']
        class_uri = row['classUri']
        count = row.get('count', '0')
        used_by_graph[graph_uri][class_uri] = count
        if 'graphLabel' in row:
            graph_labels[graph_uri] = row['graphLabel']

    print(f"  Found {len(used_by_graph)} graphs with {sum(len(v) for v in used_by_graph.values())} used classes")
    return used_by_graph, graph_labels


def get_direct_skos_relationships(endpoint, used_classes):
    """Query direct SKOS relationships between used classes."""
    # Query all SKOS relationships, then filter to used classes in Python
    query = """
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?class1 ?class2 WHERE {
      { ?class1 skos:exactMatch ?class2 }
      UNION
      { ?class1 skos:closeMatch ?class2 }
      UNION
      { ?class1 skos:broadMatch ?class2 }
      UNION
      { ?class1 skos:narrowMatch ?class2 }

      FILTER(?class1 != ?class2)
    }
    """

    print("Querying direct SKOS relationships...")
    results = query_sparql(endpoint, query)
    print(f"  Found {len(results)} total SKOS relationships")

    # Filter to only relationships between used classes
    used_set = set(used_classes)
    filtered = []
    for i, row in enumerate(results):
        if 'class1' not in row or 'class2' not in row:
            print(f"  WARNING: Row {i} missing class1 or class2: {row}")
            continue
        if row['class1'] in used_set and row['class2'] in used_set:
            filtered.append((row['class1'], row['class2']))

    print(f"  Filtered to {len(filtered)} relationships between used classes")
    return filtered


def get_wikidata_relationships(endpoint, used_classes):
    """Query Wikidata-mediated relationships between used classes."""
    # Query all Wikidata relationships, then filter in Python
    query = """
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?class ?wikidata WHERE {
      ?class ^skos:exactMatch ?wikidata .
      FILTER(STRSTARTS(STR(?wikidata), "http://www.wikidata.org/entity/"))
    }
    """

    print("Querying Wikidata relationships...")
    results = query_sparql(endpoint, query)
    print(f"  Found {len(results)} total class-to-Wikidata links")

    # Filter to only used classes and build mapping: {class_uri: wikidata_uri}
    used_set = set(used_classes)
    class_to_wikidata = {}
    for row in results:
        class_uri = row['class']
        if class_uri in used_set:
            wikidata_uri = row['wikidata']
            class_to_wikidata[class_uri] = wikidata_uri

    print(f"  Filtered to {len(class_to_wikidata)} links for used classes")
    return class_to_wikidata


def fetch_wikidata_labels(wikidata_uris):
    """Fetch labels from Wikidata for given entity URIs."""
    print("Fetching Wikidata labels...")

    labels = {}
    wikidata_endpoint = "https://query.wikidata.org/sparql"

    # Build VALUES clause with all Wikidata URIs
    values_clause = ' '.join(f"<{uri}>" for uri in wikidata_uris)

    query = f"""
    SELECT ?entity ?label WHERE {{
      VALUES ?entity {{ {values_clause} }}
      ?entity rdfs:label ?label .
      FILTER(LANG(?label) = "en")
    }}
    """

    try:
        results = query_sparql(wikidata_endpoint, query)
        for row in results:
            if 'entity' in row and 'label' in row:
                labels[row['entity']] = row['label']
        print(f"  Fetched {len(labels)} Wikidata labels")
    except Exception as e:
        print(f"  Warning: Could not fetch Wikidata labels: {e}")
        print(f"  Continuing with entity IDs as labels")

    return labels


def build_shared_class_groups(used_by_graph):
    """Find classes shared by multiple graphs."""
    print("Building shared class groups...")

    # Invert: {class_uri: [graph_uris]}
    class_to_graphs = defaultdict(list)
    for graph_uri, classes in used_by_graph.items():
        for class_uri in classes:
            class_to_graphs[class_uri].append(graph_uri)

    # Keep only classes used in 2+ graphs
    shared = {c: graphs for c, graphs in class_to_graphs.items() if len(graphs) > 1}
    print(f"  Found {len(shared)} shared classes")

    return shared


def build_skos_equivalence_classes(skos_pairs):
    """Build equivalence classes from SKOS relationships using union-find."""
    print("Building SKOS equivalence classes...")

    uf = UnionFind()

    for class1, class2 in skos_pairs:
        uf.add(class1)
        uf.add(class2)
        uf.union(class1, class2)

    groups = uf.get_groups()
    print(f"  Found {len(groups)} SKOS equivalence groups")

    return groups


def build_wikidata_groups(class_to_wikidata):
    """Group classes by their Wikidata entity."""
    print("Building Wikidata equivalence groups...")

    # Invert: {wikidata_uri: [class_uris]}
    wikidata_to_classes = defaultdict(set)
    for class_uri, wikidata_uri in class_to_wikidata.items():
        wikidata_to_classes[wikidata_uri].add(class_uri)

    # Keep only Wikidata entities linking 2+ classes
    groups = {wd: classes for wd, classes in wikidata_to_classes.items() if len(classes) > 1}
    print(f"  Found {len(groups)} Wikidata equivalence groups")

    return groups


def hash_uri(uri):
    """Generate short hash of URI for equivalence node IDs."""
    return hashlib.md5(uri.encode()).hexdigest()[:8]


def generate_equivalences(used_by_graph, graph_labels, shared_classes, skos_groups, wikidata_groups, wikidata_labels):
    """Generate equivalence data structures for TTL output."""
    equivalences = []

    # 1. Shared class equivalences
    print("\nGenerating shared class equivalences...")
    for class_uri, graph_list in shared_classes.items():
        equiv_id = f"okn:equiv-shared-{hash_uri(class_uri)}"

        # Extract label from class URI (last part after / or #)
        class_label = class_uri.split('/')[-1].split('#')[-1]

        usage = []
        for graph_uri in graph_list:
            count = used_by_graph[graph_uri][class_uri]
            usage.append((graph_uri, class_uri, count))

        equivalences.append({
            'id': equiv_id,
            'type': 'shared',
            'label': f"Shared: {class_label}",
            'sharedClass': class_uri,
            'graphs': graph_list,
            'usage': usage
        })

    print(f"  Created {len(equivalences)} shared class equivalences")

    # 2. Direct SKOS equivalences
    print("Generating direct SKOS equivalences...")
    skos_count = 0
    for equiv_class in skos_groups:
        # Find which graphs use which classes in this equivalence group
        graph_usage = {}
        for class_uri in equiv_class:
            for graph_uri in used_by_graph:
                if class_uri in used_by_graph[graph_uri]:
                    count = used_by_graph[graph_uri][class_uri]
                    # A graph might use multiple classes from this equiv group
                    if graph_uri not in graph_usage:
                        graph_usage[graph_uri] = []
                    graph_usage[graph_uri].append((class_uri, count))

        # Only create equivalence if multiple graphs are involved
        if len(graph_usage) > 1:
            equiv_id = f"okn:equiv-direct-{hash_uri(''.join(sorted(equiv_class)))}"

            # Create label from first class in set
            first_class = sorted(equiv_class)[0]
            class_label = first_class.split('/')[-1].split('#')[-1]

            usage = []
            for graph_uri, class_counts in graph_usage.items():
                for class_uri, count in class_counts:
                    usage.append((graph_uri, class_uri, count))

            equivalences.append({
                'id': equiv_id,
                'type': 'direct',
                'label': f"SKOS: {class_label}",
                'classes': list(equiv_class),
                'graphs': list(graph_usage.keys()),
                'usage': usage
            })
            skos_count += 1

    print(f"  Created {skos_count} direct SKOS equivalences")

    # 3. Wikidata equivalences
    print("Generating Wikidata equivalences...")
    wikidata_count = 0
    for wikidata_uri, class_set in wikidata_groups.items():
        # Find which graphs use which classes
        graph_usage = {}
        for class_uri in class_set:
            for graph_uri in used_by_graph:
                if class_uri in used_by_graph[graph_uri]:
                    count = used_by_graph[graph_uri][class_uri]
                    if graph_uri not in graph_usage:
                        graph_usage[graph_uri] = []
                    graph_usage[graph_uri].append((class_uri, count))

        # Only create equivalence if multiple graphs are involved
        if len(graph_usage) > 1:
            wikidata_id = wikidata_uri.split('/')[-1]
            equiv_id = f"okn:equiv-wikidata-{wikidata_id}"

            # Use Wikidata label if available, otherwise use ID
            label = wikidata_labels.get(wikidata_uri, wikidata_id)

            usage = []
            for graph_uri, class_counts in graph_usage.items():
                for class_uri, count in class_counts:
                    usage.append((graph_uri, class_uri, count))

            equivalences.append({
                'id': equiv_id,
                'type': 'wikidata',
                'label': label,
                'wikidataEntity': wikidata_uri,
                'classes': list(class_set),
                'graphs': list(graph_usage.keys()),
                'usage': usage
            })
            wikidata_count += 1

    print(f"  Created {wikidata_count} Wikidata equivalences")

    return equivalences


def generate_ttl(equivalences, graph_labels, output_file):
    """Generate TTL file from equivalence data."""
    print(f"\nGenerating TTL output to {output_file}...")

    with open(output_file, 'w') as f:
        # Write header
        f.write(f"""# Precomputed Equivalence Relationships for OKN Map
# Generated: {datetime.now().isoformat()}
# Total equivalences: {len(equivalences)}

@prefix okn: <https://purl.org/okn/> .
@prefix okns: <https://purl.org/okn/schema/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

""")

        # Write each equivalence
        for equiv in equivalences:
            equiv_id = equiv['id']

            if equiv['type'] == 'shared':
                f.write(f"\n{equiv_id} a okn:SharedClassEquivalence ;\n")
                f.write(f"    rdfs:label \"{equiv['label']}\" ;\n")
                f.write(f"    okn:sharedClass <{equiv['sharedClass']}> ;\n")

            elif equiv['type'] == 'direct':
                f.write(f"\n{equiv_id} a okn:DirectClassEquivalence ;\n")
                f.write(f"    rdfs:label \"{equiv['label']}\" ;\n")
                for class_uri in equiv['classes']:
                    f.write(f"    okn:equivalentClass <{class_uri}> ;\n")

            elif equiv['type'] == 'wikidata':
                f.write(f"\n{equiv_id} a okn:WikidataEquivalence ;\n")
                f.write(f"    rdfs:label \"{equiv['label']}\" ;\n")
                f.write(f"    okn:wikidataEntity <{equiv['wikidataEntity']}> ;\n")
                for class_uri in equiv['classes']:
                    f.write(f"    okn:equivalentClass <{class_uri}> ;\n")

            # Write graphs
            for graph_uri in equiv['graphs']:
                f.write(f"    okn:inGraph <{graph_uri}> ;\n")

            # Write usage blocks
            for i, (graph_uri, class_uri, count) in enumerate(equiv['usage']):
                is_last = (i == len(equiv['usage']) - 1)
                f.write(f"    okn:usage [\n")
                f.write(f"        okn:graph <{graph_uri}> ;\n")
                f.write(f"        okn:class <{class_uri}> ;\n")
                f.write(f"        okn:count {count}\n")
                f.write(f"    ]{'.' if is_last else ' ;'}\n")

        f.write("\n")

    print(f"  Wrote {len(equivalences)} equivalences")


def main():
    parser = argparse.ArgumentParser(description='Generate precomputed equivalence relationships')
    parser.add_argument('--endpoint', default='http://localhost:8000',
                        help='SPARQL endpoint URL (default: http://localhost:8000)')
    parser.add_argument('--output', default='../docker-backend/_precomputed_equivalences.ttl',
                        help='Output TTL file (default: ../docker-backend/_precomputed_equivalences.ttl)')
    args = parser.parse_args()

    print("OKN Map - Equivalence Generator")
    print("=" * 80)
    print(f"SPARQL Endpoint: {args.endpoint}")
    print(f"Output File: {args.output}")
    print()

    # Step 1: Get all used classes
    used_by_graph, graph_labels = get_used_classes(args.endpoint)

    all_used_classes = set()
    for classes in used_by_graph.values():
        all_used_classes.update(classes.keys())
    print(f"\nTotal unique used classes: {len(all_used_classes)}")

    # Step 2: Build equivalence groups
    shared_classes = build_shared_class_groups(used_by_graph)

    skos_pairs = get_direct_skos_relationships(args.endpoint, all_used_classes)
    skos_groups = build_skos_equivalence_classes(skos_pairs)

    class_to_wikidata = get_wikidata_relationships(args.endpoint, all_used_classes)
    wikidata_groups = build_wikidata_groups(class_to_wikidata)

    # Fetch Wikidata labels for all Wikidata entities
    wikidata_labels = fetch_wikidata_labels(list(wikidata_groups.keys()))

    # Step 3: Generate equivalence data structures
    equivalences = generate_equivalences(
        used_by_graph, graph_labels,
        shared_classes, skos_groups, wikidata_groups, wikidata_labels
    )

    # Step 4: Write TTL output
    generate_ttl(equivalences, graph_labels, args.output)

    print("\n" + "=" * 80)
    print("Equivalence generation complete!")
    print(f"Total equivalences: {len(equivalences)}")


if __name__ == '__main__':
    main()
