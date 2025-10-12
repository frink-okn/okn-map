#!/usr/bin/env python3
"""
Analyze defined vs used classes across T1 graphs in Proto-OKN.

For each T1 graph, finds:
1. Defined classes that are NOT used (defined but no instances)
2. Used classes that are NOT defined (external classes)
3. Classes that are both defined AND used (internal usage)

Usage:
  python3 analyze_class_usage.py

Prerequisites:
  Run ./run_queries.sh first to generate the input XML files
"""

import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

# Parse the SPARQL XML results
def parse_sparql_xml(filepath):
    """Parse SPARQL XML results into list of dicts"""
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Handle XML namespace
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

# Get directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
defined_file = os.path.join(script_dir, 'defined_classes.xml')
used_file = os.path.join(script_dir, 'used_classes.xml')

# Check if input files exist
if not os.path.exists(defined_file):
    print(f"Error: {defined_file} not found")
    print("Please run ./run_queries.sh first to generate the input files")
    sys.exit(1)

if not os.path.exists(used_file):
    print(f"Error: {used_file} not found")
    print("Please run ./run_queries.sh first to generate the input files")
    sys.exit(1)

# Load data
print("Loading defined classes...")
defined = parse_sparql_xml(defined_file)

print("Loading used classes...")
used = parse_sparql_xml(used_file)

print(f"\nTotal defined class entries: {len(defined)}")
print(f"Total used class entries: {len(used)}")

# Build data structures
# defined_by_graph[graph_uri] = set of class URIs defined in that graph
defined_by_graph = defaultdict(set)
graph_labels = {}

for row in defined:
    graph_uri = row['graph']
    class_uri = row['classUri']
    defined_by_graph[graph_uri].add(class_uri)
    if 'graphLabel' in row:
        graph_labels[graph_uri] = row['graphLabel']

# used_by_graph[graph_uri] = {class_uri: count}
used_by_graph = defaultdict(dict)

for row in used:
    graph_uri = row['graph']
    class_uri = row['classUri']
    count = row.get('count', '0')
    used_by_graph[graph_uri][class_uri] = count
    if 'graphLabel' in row:
        graph_labels[graph_uri] = row['graphLabel']

# Get all T1 graphs
all_graphs = sorted(set(defined_by_graph.keys()) | set(used_by_graph.keys()))

print(f"\nTotal T1 graphs: {len(all_graphs)}")
print("=" * 80)

# Analyze each graph
summary_stats = []

for graph_uri in all_graphs:
    graph_label = graph_labels.get(graph_uri, graph_uri.split('/')[-1])

    defined_classes = defined_by_graph.get(graph_uri, set())
    used_classes = set(used_by_graph.get(graph_uri, {}).keys())

    # Calculate categories
    both = defined_classes & used_classes
    defined_not_used = defined_classes - used_classes
    used_not_defined = used_classes - defined_classes

    summary_stats.append({
        'graph': graph_label,
        'uri': graph_uri,
        'defined': len(defined_classes),
        'used': len(used_classes),
        'both': len(both),
        'defined_not_used': len(defined_not_used),
        'used_not_defined': len(used_not_defined)
    })

    print(f"\n{graph_label}")
    print("-" * 80)
    print(f"  Total defined classes: {len(defined_classes)}")
    print(f"  Total used classes: {len(used_classes)}")
    print(f"  Both defined AND used (internal): {len(both)}")
    print(f"  Defined but NOT used: {len(defined_not_used)}")
    print(f"  Used but NOT defined (external): {len(used_not_defined)}")

    if defined_not_used:
        print(f"\n  Defined but not used ({len(defined_not_used)}):")
        for class_uri in sorted(defined_not_used)[:5]:
            print(f"    - {class_uri}")
        if len(defined_not_used) > 5:
            print(f"    ... and {len(defined_not_used) - 5} more")

    if used_not_defined:
        print(f"\n  Used but not defined ({len(used_not_defined)}):")
        counts = used_by_graph[graph_uri]
        for class_uri in sorted(used_not_defined, key=lambda x: int(counts.get(x, '0')), reverse=True)[:5]:
            count = counts.get(class_uri, '0')
            print(f"    - {class_uri} (count: {count})")
        if len(used_not_defined) > 5:
            print(f"    ... and {len(used_not_defined) - 5} more")

    if both:
        print(f"\n  Both defined and used ({len(both)}):")
        counts = used_by_graph[graph_uri]
        for class_uri in sorted(both, key=lambda x: int(counts.get(x, '0')), reverse=True)[:5]:
            count = counts.get(class_uri, '0')
            print(f"    - {class_uri} (count: {count})")
        if len(both) > 5:
            print(f"    ... and {len(both) - 5} more")

# Print summary table
print("\n\n" + "=" * 80)
print("SUMMARY TABLE")
print("=" * 80)
print(f"{'Graph':<30} {'Def':>6} {'Used':>6} {'Both':>6} {'Def!Use':>8} {'Use!Def':>8}")
print("-" * 80)

for stats in summary_stats:
    print(f"{stats['graph']:<30} {stats['defined']:>6} {stats['used']:>6} {stats['both']:>6} "
          f"{stats['defined_not_used']:>8} {stats['used_not_defined']:>8}")

# Overall stats
total_defined = sum(s['defined'] for s in summary_stats)
total_used = sum(s['used'] for s in summary_stats)
total_both = sum(s['both'] for s in summary_stats)
total_def_not_used = sum(s['defined_not_used'] for s in summary_stats)
total_use_not_def = sum(s['used_not_defined'] for s in summary_stats)

print("-" * 80)
print(f"{'TOTAL':<30} {total_defined:>6} {total_used:>6} {total_both:>6} "
      f"{total_def_not_used:>8} {total_use_not_def:>8}")

print("\n\nLegend:")
print("  Def      = Classes defined in this graph")
print("  Used     = Classes with usage counts in this graph")
print("  Both     = Classes both defined AND used (internal usage)")
print("  Def!Use  = Classes defined but NOT used (no instances)")
print("  Use!Def  = Classes used but NOT defined (external classes)")
