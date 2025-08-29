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
// Making the endpoint configurable by resolving it dynamically.
const oknSparqlEndpoint = ref("http://localhost:8000")
onMounted(
    async ()=>{
      try {
        let response = await fetch("/okn-map/config.json");
        const config = await response.json();
        oknSparqlEndpoint.value = config.sparqlEndpoint;
    } catch (e){
    }
})


const currentEntityDetails = ref({})

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
      'label': 'data(label)',
      'text-margin-y': '-5px'
    }
  },
  {
    selector: 'edge.import',
    style: {
      'width': 3,
      'line-color': '#00ff00',
      'target-arrow-color': '#00ff00',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier'
    }
  },
  {
    selector: 'edge.equivalent',
    style: {
      'width': 3,
      'line-color': '#87ceeb',
      'source-arrow-color': '#87ceeb',
      'source-arrow-shape': 'triangle',
      'target-arrow-color': '#87ceeb',
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
    edgeRouting: 'POLYLINE',
    fixedAlignment: 'BALANCED'
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

function shrinkEntity(entity){
  let currentShrunk = prefixes.shrink(rdf.namedNode(entity));
  if(currentShrunk){
    return currentShrunk.value;
  }
  return entity;
}

let singlefieldmappings = {
  'dct:contributor': 'contributor',
  'dct:title': 'title',
  'dct:license': 'license',
  'dct:source': 'source',
  'rdf:type': 'type',
  'pav:createdOn': 'created',
  'pav:lastUpdatedOn': 'last_updated',
}
let multiplefieldmappings = {
  'rdfs:seeAlso': 'external_links',
  'skos:definition': 'comments',
  'skos:note': 'notes',
}
let mappinglabels = {
  'title': 'Title',
  'contributor': 'Contributors',
  'license': 'License',
  'source': 'Source',
  'type': 'Entity type',
  'created': 'Creation date',
  'last_updated': 'Last updated date',
  'external_links': 'See also',
  'comments': 'External comments',
  'notes': 'Internal comments'
}

async function getDefinedClasses(evt){
  let node = evt.target;
  console.log(node);
  if(node.hasClass('expanded')){
    return;
  }
  else{
    let definedClassesQuery = `
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT distinct ?class ?classLabel WHERE {
  ?class a linkml:ClassDefinition ; skos:inScheme ${node.id().replace('_',':',1)} ; skos:exactMatch|skos:closeMatch|skos:broadMatch [].
  optional { ?class dct:title ?classLabel }
} limit 10
`
    console.log(definedClassesQuery)
    const definedClassesBindings = await myFetcher.fetchBindings(oknSparqlEndpoint.value, definedClassesQuery)
    definedClassesBindings.on('data', bindings => {
      console.log(bindings);
      let shrunkClass = prefixes.shrink(rdf.namedNode(bindings['class']['value']))
      let shrunkClassId = shrunkClass.value.replace(':','_')
      let classLabel = (bindings['classLabel'] ?? {'value': shrunkClass})['value']
      let nodeClass = node.id().replace(':','_')
      if(cyc.value.getElementById(shrunkClassId).length == 0){
        node.removeClass('collapsed')
        node.addClass('expanded')
        cyc.value.add({data: {id: shrunkClassId, label: classLabel, parent: node.id()}, classes: ['classDef', nodeClass]});
      }
    })
    definedClassesBindings.on('end', () => {
      let currentLayout = cyc.value.$('.classDef.' + node.id().replace(':','_')).layout( fcose_layout );
      currentLayout.run();
    })
  }
}

async function getEquivalentClasses(evt){
  let node = evt.target;
  const usedClassesQuery = `
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?class ?classLabel ?graph ?graphLabel WHERE {
  ${node.id().replace('_',':',1)} skos:exactMatch|skos:closeMatch|skos:broadMatch ?class .
  ?class_ linkml:class_uri ?class ; skos:inScheme ?graph .
  optional { ?class dct:title ?classLabel }
  optional { ?graph dct:title ?graphLabel }
} limit 10
  `
  console.log(usedClassesQuery)
    const definedClassesBindings = await myFetcher.fetchBindings(oknSparqlEndpoint.value, usedClassesQuery)
    definedClassesBindings.on('data', bindings => {
      console.log(bindings);
      let shrunkGraph = shrinkEntity(bindings['graph']['value'])
      let shrunkClass = shrinkEntity(bindings['class']['value'])
      let classLabel = (bindings['classLabel'] ?? {'value': shrunkClass})['value']
      let graphLabel = (bindings['graphLabel'] ?? {'value': shrunkGraph})['value']
      let shrunkGraphId = shrunkGraph.replace(':','_')
      let shrunkClassId = shrunkClass.replace(':','_')
      if(cyc.value.getElementById(shrunkGraphId).length == 0){
        cyc.value.add({data: {id: shrunkGraphId, label: graphLabel, rank: -1}, classes: ['graph','collapsed']});
      }
      if(cyc.value.getElementById(shrunkClassId).length == 0){
        cyc.value.add({data: {id: shrunkClassId, label: classLabel, parent: shrunkGraphId}, classes: ['classDef']});
      }
      cyc.value.add({group: 'edges', classes: ['equivalent'], data: {id: node.id() + '_' + shrunkClassId, source: node.id(), target: shrunkClassId }});
    })
    definedClassesBindings.on('end', () => {
      let currentLayout = cyc.value.$('.classDef.' + node.id().replace(':','_')).layout( {'name': 'circle'} );
      currentLayout.run();
    })
}

async function addUsedClasses(evt){
  let node = evt.target;
  const usedClassesQuery = `
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?graph ?class ?classLabel ?source WHERE {
  ?graph linkml:annotations/skos:example/linkml:classes/skos:example [ ?class_ [] ] .
  ?class a linkml:ClassDefinition ; linkml:class_uri ?class_ ; skos:inScheme ?source .
  optional { ?class dct:title ?classLabel }
} limit 10
  `
    const definedClassesBindings = await myFetcher.fetchBindings(oknSparqlEndpoint.value, usedClassesQuery)
    definedClassesBindings.on('data', bindings => {
      let shrunkClass = shrinkEntity(bindings['class']['value'])
      let classLabel = (bindings['classLabel'] ?? {'value': shrunkClass})['value']
      let nodeClass = node.id().replace(':','_')
      if(cyc.value.getElementById(shrunkClass.value).length == 0){
        node.removeClass('collapsed')
        node.addClass('expanded')
        cyc.value.add({data: {id: shrunkClass.value, label: classLabel, parent: node.id()}, classes: ['classDef', nodeClass]});
      }
    })
    definedClassesBindings.on('end', () => {
      let currentLayout = cyc.value.$('.classDef.' + node.id().replace(':','_')).layout( {'name': 'circle'} );
      currentLayout.run();
    })

}

async function getEntityData(evt){
  let node = evt.target;
  console.log(node);
  const entityDataQuery = `
SELECT ?p ?o WHERE {
  ${node.id().replace('_',':',1)} ?p ?o
}
  `
  console.log(entityDataQuery);

  currentEntityDetails.value = {};

  const entityDataBindings = await myFetcher.fetchBindings(oknSparqlEndpoint.value, entityDataQuery);
  entityDataBindings.on('data', bindings => {
    let shrunkP = shrinkEntity(bindings['p']['value'])
    let shrunkO = shrinkEntity(bindings['o']['value'])
    // console.log(shrunkP, shrunkO);
    if(shrunkP in singlefieldmappings){
      currentEntityDetails.value[singlefieldmappings[shrunkP]] = shrunkO;
    }
    else if(shrunkP in multiplefieldmappings){
      if(multiplefieldmappings[shrunkP] in currentEntityDetails.value)
        currentEntityDetails.value[multiplefieldmappings[shrunkP]].push(shrunkO);
      else
        currentEntityDetails.value[multiplefieldmappings[shrunkP]] = [shrunkO];
    }
  });
  entityDataBindings.on('end', () => {
    currentEntityDetails.value = currentEntityDetails.value;
  })
}

async function getGraphImports(evt){
  let node = evt.target;
  console.log(node);
const importsQuery = `
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>

SELECT ?s ?sLabel ?o ?oLabel WHERE {
  VALUES ?s { ${node.id().replace('_',':',1)} }
  ?s linkml:imports ?o .
  optional { ?s dct:title ?sLabel }
  optional { ?o dct:title ?oLabel }
} limit 100
`

  const importsBindings = await myFetcher.fetchBindings(oknSparqlEndpoint.value, importsQuery)
  importsBindings.on('data', bindings => {
    console.log(bindings)
    let shrunkS = shrinkEntity(bindings['s']['value'])
    let shrunkO = shrinkEntity(bindings['o']['value'])
    let sLabel = (bindings['sLabel'] ?? {'value': shrunkS})['value']
    let oLabel = (bindings['oLabel'] ?? {'value': shrunkO})['value']
    let shrunkSId = shrunkS.replace(':','_')
    let shrunkOId = shrunkO.replace(':','_')
    if(cyc.value.getElementById(shrunkSId).length == 0){
      cyc.value.add({group: 'nodes', data: {id: shrunkSId, label: sLabel, rank: -1}, classes: ['graph','collapsed']});
    }
    cyc.value.$("#" + shrunkSId).removeClass('importsMissing')
    cyc.value.$("#" + shrunkSId).addClass('importsAdded')
    let previousRank = cyc.value.$("#" + shrunkSId).data('rank');
    if(cyc.value.getElementById(shrunkOId).length == 0){
      cyc.value.add({group: 'nodes', data: {id: shrunkOId, label: oLabel, rank: previousRank - 1}, classes: ['graph','collapsed','importsMissing']});
    }
    else{
      cyc.value.$("#" + shrunkOId).removeClass('importsMissing')
    }
    cyc.value.add({group: 'edges', classes: ['import'], data: {id: shrunkSId + '_' + shrunkOId, source: shrunkSId, target: shrunkOId }});
  });
  importsBindings.on('end', () => {
    cyc.value.$('.graph').layout(
      klay_layout
    ).run();
  })
}

onMounted(async () => {
  cyc.value = cytoscape({
    container: document.getElementsByClassName('cy-wrapper')[0],
    elements: [ // TODO: currently hardcoding T1s
      {group: 'nodes', data: {id: 'okns_biobricks-ice', label: 'BioBricks-ICE', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_biobricks-ice']},
      {group: 'nodes', data: {id: 'okns_climatemodelskg', label: 'ClimateModels-KG', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_climatemodelskg']},
      {group: 'nodes', data: {id: 'okns_dreamkg', label: 'DREAM-KG', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_dreamkg']},
      {group: 'nodes', data: {id: 'okns_ruralkg', label: 'Rural-KG', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_ruralkg']},
      {group: 'nodes', data: {id: 'okns_sockg', label: 'SOC-KG', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_sockg']},
      {group: 'nodes', data: {id: 'okns_sudokn', label: 'SUD-OKN', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_sudokn']},
      {group: 'nodes', data: {id: 'okns_wildlifekn', label: 'KN-Wildlife', rank: 0}, classes: ['graph','collapsed','t1','importsMissing','okns_wildlifekn']},
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

  cyc.value.on('click', 'node', getEntityData);
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

  cyc.value.on('tap', function(event){
    // target holds a reference to the originator
    // of the event (core or element)
    var evtTarget = event.target;
    cyc.value.fit()
    if( evtTarget === cyc.value ){
      console.log('tap on background');
    }
    else{
      cyc.value.$("*").not(event.target).style('opacity', '0.5')
    }
  });
  cyc.value.on('mouseover', function(){})
  cyc.value.on('mouseout', function(){})
});

const visibleTab = ref('help')
</script>

<template>
  <div class="app-wrapper">
    <div class="main-content">
      <div class="cy-wrapper"></div>
    </div>
    <div class="sidebar">
      <div class="tab-controls">
        <span class="control-icon" @click="visibleTab='key'" title="Key to symbols">𓃑</span>
        <span class="control-icon" @click="visibleTab='details'" title="Entity details">📖</span>
        <span class="control-icon" @click="visibleTab='help'" title="About the map">ℹ️</span>
      </div>
      <div class="tab-content">
        <template v-if="visibleTab == 'key'">
          <h5>Key to symbols</h5>
          <ul>
            <li>Green dot: Theme 1 graphs</li>
            <li>Gray dot: External ontologies (referred to by Theme 1 graphs)</li>
            <li>Gray square: External ontology with classes defined in it</li>
            <li>Red dot: Class (entity type)</li>
          </ul>
        </template>
        <template v-else-if="visibleTab == 'details'">
          <h5>Entity details</h5>
          <table class="entity-details-table">
            <tr v-for="(value, key) in currentEntityDetails">
              <td style="border-right: 1px solid pink;">{{ mappinglabels[key] }}</td>
              <td style="border-bottom: 1px solid pink;">
                <template v-if="Array.isArray(value)">
                  <template v-for="element in value">
                    <template v-if="['external_links'].includes(key)"><a :href='element'>{{ element }}</a></template>
                    <template v-else>{{element}}</template>
                    <br/>
                  </template>
                </template>
                <template v-else-if="['license','contributor'].includes(key)">
                  <a :href='value'>{{ value }}</a>
                </template>
                <template v-else>
                  {{ value }}
                </template>
              </td>
            </tr>
          </table>
        </template>
        <template v-else>
          <h5>About the OKN Map</h5>
          <section>
            <p>This is a prototype of the Proto-OKN Map.</p>
            <p>It is generated through the following series of steps:</p>
            <ul>
              <li>RDF data is processed into a LinkML schema using <a href="https://github.com/frink-okn/schema-gen" target="_blank">a set of scripts</a>.</li>
              <li>This schema is then itself turned into RDF using <a href="https://linkml.io/linkml/generators/rdf.html" target="_blank">the LinkML runtime's RDF generator</a>.</li>
              <li>The RDF representation of that schema is then directly queried with SPARQL using this interface.</li>
            </ul>
          </section>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.entity-details-table td:nth-child(1){
  text-align: right;
}
.entity-details-table td:nth-child(2){
  text-align: left;
}
</style>
