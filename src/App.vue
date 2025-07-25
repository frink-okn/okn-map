<script setup lang="ts">
import { ref, onMounted } from 'vue';
import rdf from '@rdfjs/data-model'
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
import klay from 'cytoscape-klay'
import { SparqlEndpointFetcher } from 'fetch-sparql-endpoint';
import { prefixes } from './prefixes.js'
import cytoscapeExpandCollapse from 'https://cdn.jsdelivr.net/npm/cytoscape-expand-collapse@4.1.1/+esm'
import cytoscapeUndoRedo from 'https://cdn.jsdelivr.net/npm/cytoscape-undo-redo@1.3.3/+esm'

cytoscapeUndoRedo(cytoscape)
cytoscapeExpandCollapse(cytoscape)

const oknSparqlEndpoint = 'http://localhost:8000'

const myFetcher = new SparqlEndpointFetcher({
  defaultHeaders: new Headers({"User-Agent": "OKN Map <mmorshed@scripps.edu>"})
});
const cyc = ref()
const ecApi = ref()
const graphLayout = ref()

const graphStyle = ref([ // the stylesheet for the graph
  {
    selector: 'node',
    style: {
      'label': 'data(id)'
    }
  },
  {
    selector: 'edge',
    style: {
      'width': 3,
      'line-color': '#ccc',
      'target-arrow-color': '#ccc',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier'
    }
  },
  {
    selector: ".t1",
    style: {
      'background-color': 'green'
    }
  },
  {
    selector: ".graph",
    style: {
      'border-color': 'black',
      'border-width': '3px',
    }
  },
  {
    selector: ".classDef",
    style: {
      'background-color': 'red'
    }
  },
]);

cytoscape.use(klay);
let klay_layout = {
  name: "klay",
  animate: true,
  nodeDimensionsIncludeLabels: true,
  klay: {
    spacing: 40,
    direction: 'DOWN',
    edgeRouting: 'POLYLINE'
  }
}

cytoscape.use(fcose);
let fcose_layout = {
  name: "fcose",
  nodeDimensionsIncludeLabels: true,
  animate: true,
  randomize: false,
  fit: true
}

async function getDefinedClasses(evt){
  let node = evt.target;
  console.log(node);
  if(node.hasClass('expanded')){
    return;
  }
  else{
    let definedClassesQuery = `
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT distinct ?class WHERE {
  ?class a linkml:ClassDefinition ; skos:inScheme ${node.id().replace('_',':',1)} ; skos:exactMatch|skos:closeMatch|skos:broadMatch [].
} limit 10
`
    console.log(definedClassesQuery)
    const definedClassesBindings = await myFetcher.fetchBindings(oknSparqlEndpoint, definedClassesQuery)
    definedClassesBindings.on('data', bindings => {
      console.log(bindings);
      let shrunkClass = prefixes.shrink(rdf.namedNode(bindings['class']['value']))
      let nodeClass = node.id().replace(':','_')
      if(cyc.value.getElementById(shrunkClass.value.replace(':','_')).length == 0){
        node.removeClass('collapsed')
        node.addClass('expanded')
        cyc.value.add({data: {id: shrunkClass.value.replace(':','_'), parent: node.id()}, classes: ['classDef', nodeClass]});
      }
    })
    definedClassesBindings.on('end', () => {
      let currentLayout = cyc.value.$('.classDef.' + node.id().replace(':','_')).layout( fcose_layout );
      currentLayout.run();
    })
  }
}

async function getEquivalentClasses(evt){ // TODO FINISH
  let node = evt.target;
  const usedClassesQuery = `
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?class ?graph WHERE {
  ${node.id().replace('_',':',1)} skos:exactMatch|skos:closeMatch|skos:broadMatch ?class .
  ?class_ linkml:class_uri ?class ; skos:inScheme ?graph .
} limit 10
  `
  console.log(usedClassesQuery)
    const definedClassesBindings = await myFetcher.fetchBindings(oknSparqlEndpoint, usedClassesQuery)
    definedClassesBindings.on('data', bindings => {
      let shrunkGraph = prefixes.shrink(rdf.namedNode(bindings['graph']['value']))
      let shrunkClass = prefixes.shrink(rdf.namedNode(bindings['class']['value']))
      if(cyc.value.getElementById(shrunkGraph.value).length == 0){
        cyc.value.add({data: {id: shrunkGraph.value.replace(':','_'), rank: -1}, classes: ['graph','collapsed']});
      }
      if(cyc.value.getElementById(shrunkClass.value).length == 0){
        cyc.value.add({data: {id: shrunkClass.value.replace(':','_'), parent: shrunkGraph.value.replace(':','_')}, classes: ['classDef']});
      }
      cyc.value.add({group: 'edges', data: {id: node.id() + '_' + shrunkClass.value.replace(':','_'), source: node.id(), target: shrunkClass.value.replace(':','_') }});
    })
    definedClassesBindings.on('end', () => {
      let currentLayout = cyc.value.$('.classDef.' + node.id().replace(':','_')).layout( {'name': 'circle'} );
      currentLayout.run();
    })
}

async function addUsedClasses(evt){
  let node = evt.target;
  const usedClassesQuery = `
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?graph ?class ?source WHERE {
  ?graph linkml:annotations/skos:example/linkml:classes/skos:example [ ?class_ [] ] .
  ?class a linkml:ClassDefinition ; linkml:class_uri ?class_ ; skos:inScheme ?source .
} limit 10
  `
    const definedClassesBindings = await myFetcher.fetchBindings(oknSparqlEndpoint, usedClassesQuery)
    definedClassesBindings.on('data', bindings => {
      let shrunkClass = prefixes.shrink(rdf.namedNode(bindings['class']['value']))
      let nodeClass = node.id().replace(':','_')
      if(cyc.value.getElementById(shrunkClass.value).length == 0){
        node.removeClass('collapsed')
        node.addClass('expanded')
        cyc.value.add({data: {id: shrunkClass.value, parent: node.id()}, classes: ['classDef', nodeClass]});
      }
    })
    definedClassesBindings.on('end', () => {
      let currentLayout = cyc.value.$('.classDef.' + node.id().replace(':','_')).layout( {'name': 'circle'} );
      currentLayout.run();
    })

}

async function getGraphImports(evt){
  let node = evt.target;
  console.log(node);
const importsQuery = `
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>

SELECT ?s ?o WHERE {
  VALUES ?s { ${node.id().replace('_',':',1)} }
  ?s linkml:imports ?o .
} limit 100
`

  const importsBindings = await myFetcher.fetchBindings(oknSparqlEndpoint, importsQuery)
  importsBindings.on('data', bindings => {
    console.log(bindings)
    let shrunkS = prefixes.shrink(rdf.namedNode(bindings['s']['value']))
    let shrunkO = prefixes.shrink(rdf.namedNode(bindings['o']['value']))
    if(! shrunkO){
      shrunkO = rdf.namedNode(bindings['o']['value'])
    }
    if(cyc.value.getElementById(shrunkS.value.replace(':','_')).length == 0){
      cyc.value.add({group: 'nodes', data: {id: shrunkS.value.replace(':','_'), rank: -1}, classes: ['graph','collapsed']});
    }
    cyc.value.$("#" + shrunkS.value.replace(':','_')).removeClass('importsMissing')
    cyc.value.$("#" + shrunkS.value.replace(':','_')).addClass('importsAdded')
    let previousRank = cyc.value.$("#" + shrunkS.value.replace(':','_')).data('rank');
    if(cyc.value.getElementById(shrunkO.value.replace(':','_')).length == 0){
      cyc.value.add({group: 'nodes', data: {id: shrunkO.value.replace(':','_'), rank: previousRank - 1}, classes: ['graph','collapsed','importsMissing']});
    }
    else{
      cyc.value.$("#" + shrunkO.value.replace(':','_')).removeClass('importsMissing')
    }
    cyc.value.add({group: 'edges', data: {id: shrunkS.value.replace(':','_') + '_' + shrunkO.value.replace(':','_'), source: shrunkS.value.replace(':','_'), target: shrunkO.value.replace(':','_') }});
  });
  importsBindings.on('end', () => {
    cyc.value.$('.graph').layout(
      klay_layout
    ).run();
  })
}

onMounted(async () => {
  cyc.value = cytoscape({
    container: document.getElementById('cy-wrapper'),
    elements: [ // TODO: currently hardcoding T1s
      {group: 'nodes', data: {id: 'okns_biobricks-ice', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_biobricks-ice']},
      {group: 'nodes', data: {id: 'okns_climatemodelskg', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_climatemodelskg']},
      {group: 'nodes', data: {id: 'okns_dreamkg', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_dreamkg']},
      {group: 'nodes', data: {id: 'okns_ruralkg', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_ruralkg']},
      {group: 'nodes', data: {id: 'okns_sockg', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_sockg']},
      {group: 'nodes', data: {id: 'okns_sudokn', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_sudokn']},
      {group: 'nodes', data: {id: 'okns_wildlifekn', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_wildlifekn']},
    ],
    style: graphStyle.value
  });
  console.log('Starting!')

  ecApi.value = cyc.value.expandCollapse({
    layoutBy: fcose_layout,
    fisheye: true,
    animate: true,
    // expandCueImage: "icon-plus.png",
    // collapseCueImage: "icon-minus.png"
  })

  cyc.value.on('click', '.graph.importsMissing', getGraphImports)
  cyc.value.on('click', '.graph.importsAdded', getDefinedClasses)
  cyc.value.on('click', '.classDef', getEquivalentClasses)
  cyc.value.$('.graph').layout(
    klay_layout
  ).run();
  cyc.value.on('ready', function(){
    cyc.value.center()
    console.log(cyc.value.elements().boundingBox())
  })
});
</script>

<template>
  <div id="cy-wrapper" style="height:75vh;width:80vw;border:1px solid white;"></div>
</template>

<style scoped>
.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.vue:hover {
  filter: drop-shadow(0 0 2em #42b883aa);
}
</style>
