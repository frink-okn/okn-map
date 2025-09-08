<script setup lang="ts">
import { ref, onMounted, toRaw } from 'vue';
import rdf from '@rdfjs/data-model'
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
import klay from 'cytoscape-klay'
import { SparqlEndpointFetcher } from 'fetch-sparql-endpoint';
import { prefixes } from './prefixes.js'
import cytoscapeUndoRedo from 'https://cdn.jsdelivr.net/npm/cytoscape-undo-redo@1.3.3/+esm'
import contextMenus from 'cytoscape-context-menus';

cytoscapeUndoRedo(cytoscape)
cytoscape.use(contextMenus)
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

let usecases = [
  // TODO: set positions relative to size of initial viewport?
  {group: 'nodes', data: {id: 'usecase_bio', label: 'Biology and Health'}, classes: ['usecase','usecase_bio'], position: {x: -100, y: 0}, locked: true},
  {group: 'nodes', data: {id: 'usecase_env', label: 'Environment'}, classes: ['usecase','usecase_env'], position: {x: 550, y: 0}, locked: true},
  // {group: 'nodes', data: {id: 'usecase_help', label: 'Help!'}, classes: ['usecase','usecase_help'], position: {x: 225, y: 125}, locked: true},
  {group: 'nodes', data: {id: 'usecase_jus', label: 'Justice'}, classes: ['usecase','usecase_jus'], position: {x: -100, y: 250}, locked: true},
  {group: 'nodes', data: {id: 'usecase_tam', label: 'Technology and Manufacturing'}, classes: ['usecase','usecase_tam'], position: {x: 550, y: 250}, locked: true},
]

let t1graphs = {
    // TODO: currently hardcoding T1s; move to configuration file?
  // TODO: set positions relative to use case location
  'usecase_bio': [
    {group: 'nodes', data: {id: 'okns_biobricks-ice', label: 'BioBricks-ICE', rank: 0}, classes: ['graph','collapsed','t1','t1_bio','importsMissing','okns_biobricks-ice'], position: {x: -150, y: -50}},
    {group: 'nodes', data: {id: 'okns_spoke', label: 'SPOKE', rank: 0}, classes: ['graph','collapsed','t1','t1_bio','importsMissing','okns_spoke'], position: {x: -50, y: -50}}
  ],
  'usecase_env': [
    {group: 'nodes', data: {id: 'okns_climatemodelskg', label: 'ClimateModels-KG', rank: 0}, classes: ['graph','collapsed','t1_env','importsMissing','okns_climatemodelskg'], position: {x: 500, y: -50}},
    {group: 'nodes', data: {id: 'okns_fiokg', label: 'SAWGRAPH FIO', rank: 0}, classes: ['graph','collapsed','t1','t1_env','importsMissing','okns_fiokg'], position: {x: 625, y: 75}},
    {group: 'nodes', data: {id: 'okns_hydrologykg', label: 'SAWGRAPH Hydrology', rank: 0}, classes: ['graph','collapsed','t1','t1_env','importsMissing','okns_hydrologykg'], position: {x: 550, y: 75}},
    {group: 'nodes', data: {id: 'okns_sawgraph', label: 'SAWGRAPH', rank: 0}, classes: ['graph','collapsed','t1','t1_env','importsMissing','okns_sawgraph'], position: {x: 487, y: 25}},
    {group: 'nodes', data: {id: 'okns_sockg', label: 'SOC-KG', rank: 0}, classes: ['graph','collapsed','t1','t1_env','importsMissing','okns_sockg'], position: {x: 575, y: 0}},
    {group: 'nodes', data: {id: 'okns_spatialkg', label: 'SAWGRAPH Spatial', rank: 0}, classes: ['graph','collapsed','t1','t1_env','importsMissing','okns_spatialkg'], position: {x: 625, y: 75}},
    {group: 'nodes', data: {id: 'okns_ufokn', label: 'WEN-OKN', rank: 0}, classes: ['graph','collapsed','t1','t1_env','importsMissing','okns_ufokn'], position: {x: 475, y: 75}},
    {group: 'nodes', data: {id: 'okns_wildlifekn', label: 'KN-Wildlife', rank: 0}, classes: ['graph','collapsed','t1','t1_env','importsMissing','okns_wildlifekn'], position: {x:625, y: -50}},
  ],
  'usecase_jus': [
    {group: 'nodes', data: {id: 'okns_dreamkg', label: 'DREAM-KG', rank: 0}, classes: ['graph','collapsed','t1','t1_jus','importsMissing','okns_dreamkg'], position: {x: -25, y: 225}},
  // {group: 'nodes', data: {id: 'okns_nikg', label: 'NIKG', rank: 0}, classes: ['graph','collapsed','t1','t1_jus','importsMissing','okns_nikg'], position: {x: 625, y: 75}},
    {group: 'nodes', data: {id: 'okns_ruralkg', label: 'Rural-KG', rank: 0}, classes: ['graph','collapsed','t1','t1_jus','importsMissing','okns_ruralkg'], position: {x: -175, y: 325}},
    {group: 'nodes', data: {id: 'okns_scales', label: 'SCALES', rank: 0}, classes: ['graph','collapsed','t1','t1_jus','importsMissing','okns_scales'], position: {x: -175, y: 250}},
  ],
  'usecase_tam': [
    {group: 'nodes', data: {id: 'okns_securechainkg', label: 'Secure Chain', rank: 0}, classes: ['graph','collapsed','t1','t1_tam','importsMissing','okns_securechainkg'], position: {x: 625, y: 200}},
    {group: 'nodes', data: {id: 'okns_sudokn', label: 'SUD-OKN', rank: 0}, classes: ['graph','collapsed','t1','t1_tam','importsMissing','okns_sudokn'], position: {x: 475, y: 200}}
  ]
}

const initialElements = ref(usecases)

const graphStyle = ref([ // the stylesheet for the graph
  {
    selector: 'node',
    style: {
      'label': 'data(label)',
      'text-margin-y': '-5px'
    }
  },
  // starting region styling
  {
    selector: '.usecase',
    style: {
      'width': '15em',
      'height': '12.5em',
      'background-width': '80%',
      'background-height': '100%',
      'background-color': '#e8e4ef',
      'shape': 'round-rectangle',
      'text-opacity': '0'
    }
  },
  {selector: '.usecase_bio', style: {'background-image': 'static/Biology-Health-1.png'}},
  {selector: '.usecase_jus', style: {'background-image': 'static/Biology-Health-2.png'}},
  {selector: '.usecase_env', style: {'background-image': 'static/Biology-Health-3.png'}},
  {selector: '.usecase_tam', style: {'background-image': 'static/Biology-Health-4.png'}},
  {selector: '.usecase_help', style: {'z-index': -5, 'opacity': 0.25, 'width': '25em', 'height': '25em'}},
  // edge styling
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
    selector: 'edge.classuse',
    style: {
      'width': 3,
      'label': 'data(label)',
      'line-color': '#f4a460',
      'target-arrow-color': '#f4a460',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier'
    }
  },
  // entity node styling
  {selector: ".t1_bio", style: {'background-color': 'khaki'}},
  {selector: ".t1_env", style: {'background-color': 'chartreuse'}},
  {selector: ".t1_jus", style: {'background-color': 'dodgerblue'}},
  {selector: ".t1_tam", style: {'background-color': 'indianred'}},
  {selector: ".classDef", style: {'background-color': 'red', 'border-color': 'black', 'border-width': '3px'}},
  {
    selector: ".graph",
    style: {
      'border-color': 'black',
      'border-width': '3px',
      'border-opacity': '0.5',
      'text-opacity': '0.5'
    }
  },
  {
    selector: ".graph.hovered",
    style: {'border-opacity': '1', 'text-opacity': '1'}
  }
]);

cytoscape.use(klay);
let klay_layout = {
  name: "klay",
  animate: true,
  fit: false,
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
  fit: false
}

const nodesToFocus = ref([])
const nodesAdded = ref([])

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
  'linkml:uri': 'uri',
  'linkml:class_uri': 'uri',
  'linkml:slot_uri': 'uri'
}
let multiplefieldmappings = {
  'rdfs:seeAlso': 'external_links',
  'skos:definition': 'comments',
  'skos:note': 'notes',
  'linkml:slots': 'slots',
  'linkml:domain': 'domain',
  'linkml:domain_of': 'domain',
  'linkml:range': 'range'
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
  'notes': 'Internal comments',
  'slots': 'Predicates',
  'domain': 'Domain',
  'range': 'Range'
}

async function getDefinedClasses(evt){
  let node = evt.target;
  console.log(node);
  if(node.hasClass('expanded')){
    return;
  }
  else{
    let {x: nodex, y: nodey} = node.position();
    let definedClassesQuery = `
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT distinct ?class ?classLabel WHERE {
  ?class a linkml:ClassDefinition ; skos:inScheme ${node.id().replace('_',':',1)} ; linkml:class_uri ?classuri .
  [] linkml:tag okns:counts ; skos:example [ linkml:classes [ skos:example [ ?classuri [] ] ] ]
  optional { ?class dct:title ?classLabel }
} limit 10
`
    console.log(definedClassesQuery)
    const definedClassesBindings = await myFetcher.fetchBindings(oknSparqlEndpoint.value, definedClassesQuery)
    definedClassesBindings.on('data', bindings => {
      console.log(bindings);
      let shrunkClass = shrinkEntity(bindings['class']['value'])
      let shrunkClassId = shrunkClass.replace(':','_')
      let classLabel = (bindings['classLabel'] ?? {'value': shrunkClass})['value']
      let nodeClass = node.id().replace(':','_')
      if(cyc.value.getElementById(shrunkClassId).length == 0){
        node.removeClass('collapsed')
        node.addClass('expanded')
        cyc.value.add({data: {id: shrunkClassId, label: classLabel, parent: node.id()}, classes: ['classDef', nodeClass]});
      }
    })
    definedClassesBindings.on('end', () => {
      let currentLayout = cyc.value.$('.classDef.' + node.id().replace(':','_')).layout( {
        // fcose_layout,
          name: 'grid',
          fit: false,
          boundingBox: {x1: nodex, y1: nodey, w: 100, h: 100},
      } );
      currentLayout.run();
    })
  }
}

async function getAllEquivalentClasses(evt){
  let node = evt.target;
  const usedClassesQuery = `
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?c1 ?c1Label ?class ?classLabel ?graph ?graphLabel WHERE {
  ?c1 skos:inScheme ${node.id().replace('_',':',1)} .
  { ?c1 skos:exactMatch|skos:closeMatch|skos:broadMatch ?class_ }
  union
  { ?c1 linkml:class_uri ?c1_ . ?c1_ ^skos:exactMatch/skos:exactMatch ?class_  }
  ?class linkml:class_uri ?class_ ; skos:inScheme ?graph . filter(?graph != ${node.id().replace('_',':',1)})
  optional { ?class dct:title ?classLabel }
  optional { ?graph dct:title ?graphLabel }
} limit 10
  `
nodesToFocus.value.push('#'+node.id())
  console.log(usedClassesQuery)
    const definedClassesBindings = await myFetcher.fetchBindings(oknSparqlEndpoint.value, usedClassesQuery)
    definedClassesBindings.on('data', bindings => {
      console.log(bindings);
      let shrunkC1 = shrinkEntity(bindings['c1']['value'])
      let shrunkGraph = shrinkEntity(bindings['graph']['value'])
      let shrunkClass = shrinkEntity(bindings['class']['value'])
      let c1Label = (bindings['c1Label'] ?? {'value': shrunkC1})['value']
      let classLabel = (bindings['classLabel'] ?? {'value': shrunkClass})['value']
      let graphLabel = (bindings['graphLabel'] ?? {'value': shrunkGraph})['value']
      let shrunkC1Id = shrunkC1.replace(':','_')
      let shrunkGraphId = shrunkGraph.replace(':','_')
      let shrunkClassId = shrunkClass.replace(':','_')
      if(cyc.value.getElementById(shrunkC1Id).length == 0){
        cyc.value.add({data: {id: shrunkC1Id, label: c1Label, parent: node.id()}, classes: ['classDef']});
        nodesAdded.value.push('#'+shrunkC1Id)
      }
      nodesToFocus.value.push('#'+shrunkC1Id)
      if(cyc.value.getElementById(shrunkGraphId).length == 0){
        cyc.value.add({data: {id: shrunkGraphId, label: graphLabel, rank: -1}, classes: ['graph','collapsed']});
        nodesAdded.value.push('#'+shrunkGraphId)
      }
      nodesToFocus.value.push('#'+shrunkGraphId)
      if(cyc.value.getElementById(shrunkClassId).length == 0){
        cyc.value.add({data: {id: shrunkClassId, label: classLabel, parent: shrunkGraphId}, classes: ['classDef']});
        nodesAdded.value.push('#'+shrunkClassId)
      }
      nodesToFocus.value.push('#'+shrunkClassId)
      cyc.value.add({group: 'edges', classes: ['equivalent'], data: {id: shrunkC1Id + '_' + shrunkClassId, source: shrunkC1Id, target: shrunkClassId }});
    })
    definedClassesBindings.on('end', () => {
      cyc.value.$(nodesToFocus.value.join(', ')).style('opacity', '1');
      cyc.value.$("*").not(nodesToFocus.value.join(', ')).style('opacity', '0.25');
      if(nodesAdded.value.length > 1){
        cyc.value.$(nodesAdded.value.join(', ')).layout(
          {
            name: 'grid',
            fit: false,
            boundingBox: {x1: 50, y1: -50, x2: 375, y2: 300},
          }
        ).run();
        nodesAdded.value = [];
      }
    })
  cyc.value.$('#'+node.id()).style('opacity', '1');
  nodesToFocus.value = [];
}

async function getEquivalentClasses(evt){
  let node = evt.target;
  const usedClassesQuery = `
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?class ?classLabel ?graph ?graphLabel WHERE {
  { ${node.id().replace('_',':',1)} skos:exactMatch|skos:closeMatch|skos:broadMatch ?class_ }
  union
  { ${node.id().replace('_',':',1)} linkml:class_uri ?c1_ . ?c1_ ^skos:exactMatch/skos:exactMatch ?class_  }
  ?class linkml:class_uri ?class_ ; skos:inScheme ?graph . filter(?class != ${node.id().replace('_',':',1)})
  optional { ?class dct:title ?classLabel }
  optional { ?graph dct:title ?graphLabel }
} limit 10
  `
nodesToFocus.value.push('#'+node.id())
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
        nodesAdded.value.push('#'+shrunkGraphId)
      }
      nodesToFocus.value.push('#'+shrunkGraphId)
      if(cyc.value.getElementById(shrunkClassId).length == 0){
        cyc.value.add({data: {id: shrunkClassId, label: classLabel, parent: shrunkGraphId}, classes: ['classDef']});
        nodesAdded.value.push('#'+shrunkClassId)
      }
      nodesToFocus.value.push('#'+shrunkClassId)
      cyc.value.add({group: 'edges', classes: ['equivalent'], data: {id: node.id() + '_' + shrunkClassId, source: node.id(), target: shrunkClassId }});
    })
    definedClassesBindings.on('end', () => {
      cyc.value.$(nodesToFocus.value.join(', ')).style('opacity', '1');
      cyc.value.$("*").not(nodesToFocus.value.join(', ')).style('opacity', '0.25');
      if(nodesAdded.value.length > 1){
        cyc.value.$(nodesAdded.value.join(', ')).layout(
          {
            name: 'grid',
            fit: false,
            boundingBox: {x1: 50, y1: -50, x2: 375, y2: 300},
          }
        ).run();
        nodesAdded.value = [];
      }
    })
  cyc.value.$('#'+node.id()).style('opacity', '1');
  nodesToFocus.value = [];
}

async function getAllUsedClasses(evt){
  let node = evt.target;
  const usedClassesQuery = `
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX linkml: <https://w3id.org/linkml/>
PREFIX okn: <https://purl.org/okn/>
PREFIX okns: <https://purl.org/okn/schema/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?graph ?graphLabel ?class ?classLabel ?count WHERE {
  ${node.id().replace('_',':',1)} linkml:annotations [ linkml:tag okns:counts ; skos:example/linkml:classes/skos:example [ ?class_ ?s ] ] .
  ?class a linkml:ClassDefinition ; linkml:class_uri ?class_ ; skos:inScheme ?graph .
  optional { ?graph dct:title ?graphLabel }
  optional { ?class dct:title ?classLabel }
  ?s ?p ?count .
  filter(?p = skos:example)
} limit 10
`
nodesToFocus.value.push('#'+node.id())
const definedClassesBindings = await myFetcher.fetchBindings(oknSparqlEndpoint.value, usedClassesQuery)
    definedClassesBindings.on('data', bindings => {
      let shrunkGraph = shrinkEntity(bindings['graph']['value'])
      let shrunkClass = shrinkEntity(bindings['class']['value'])
      let classLabel = (bindings['classLabel'] ?? {'value': shrunkClass})['value']
      let graphLabel = (bindings['graphLabel'] ?? {'value': shrunkGraph})['value']
      let shrunkGraphId = shrunkGraph.replace(':','_')
      let shrunkClassId = shrunkClass.replace(':','_')
      if(cyc.value.getElementById(shrunkGraphId).length == 0){
        cyc.value.add({data: {id: shrunkGraphId, label: graphLabel, rank: -1}, classes: ['graph','collapsed']});
      }
      nodesToFocus.value.push('#'+shrunkGraphId)
      if(cyc.value.getElementById(shrunkClassId).length == 0){
        cyc.value.add({data: {id: shrunkClassId, label: classLabel, parent: shrunkGraphId}, classes: ['classDef']});
        nodesAdded.value.push('#'+shrunkClassId)
      }
      nodesToFocus.value.push('#'+shrunkClassId)
      if(shrunkGraphId != node.id()){
        cyc.value.add({group: 'edges', classes: ['classuse'], data: {label: bindings['count']['value'] ?? '', id: node.id() + '_' + shrunkClassId, source: node.id(), target: shrunkClassId }});
      }
    })
    definedClassesBindings.on('end', () => {
      console.log(nodesToFocus.value, nodesAdded.value);
      cyc.value.$(nodesToFocus.value.join(', ')).style('opacity', '1');
      cyc.value.$("*").not(nodesToFocus.value.join(', ')).style('opacity', '0.25');
      if(nodesAdded.value.length > 1){
        cyc.value.$(nodesAdded.value.join(', ')).layout(
          {
            name: 'grid',
            fit: false,
            boundingBox: {x1: 50, y1: -50, x2: 375, y2: 300},
          }
        ).run();
        nodesAdded.value = [];
      }
    })
  cyc.value.$('#'+node.id()).style('opacity', '1');
  nodesToFocus.value = [];
}

async function showEntityData(evt){
  let node = evt.target;
  if(node === toRaw(cyc.value) || node.classes().includes('usecase'))
    return;
  console.log(node);
  cyc.value.$('#'+node.id()).style('opacity', '1');
  await getEntityData(node.id(), node.id().replace('_',':',1), node.classes())
}

async function getEntityData(nodeid, nodeidreplaced, nodeclasses){
  const entityDataQuery = `
SELECT ?p ?o WHERE {
  { ${nodeidreplaced} ?p ?o }
   union
  { ${nodeidreplaced} linkml:any_of/linkml:range ?o . bind(linkml:range as ?p) }
}
  `
  console.log(entityDataQuery);

  currentEntityDetails.value = {}

  const entityDataBindings = await myFetcher.fetchBindings(oknSparqlEndpoint.value, entityDataQuery);
  entityDataBindings.on('data', bindings => {
    let shrunkP = shrinkEntity(bindings['p']['value'])
    let shrunkO = shrinkEntity(bindings['o']['value'])
    console.log(shrunkP, shrunkO);
    if(['linkml:slots'].includes(shrunkP) && nodeclasses.includes('graph'))
      return;
    if(shrunkP in singlefieldmappings){
      currentEntityDetails.value[singlefieldmappings[shrunkP]] = shrunkO;
    }
    else if(shrunkP in multiplefieldmappings){
      if(multiplefieldmappings[shrunkP] in currentEntityDetails.value)
        currentEntityDetails.value[multiplefieldmappings[shrunkP]].add(shrunkO);
      else
        currentEntityDetails.value[multiplefieldmappings[shrunkP]] = new Set([shrunkO]);
    }
  });
  entityDataBindings.on('end', () => {
    currentEntityDetails.value = currentEntityDetails.value;
    visibleTab.value = 'details'
  })
  cyc.value.$('#'+nodeid).style('opacity', '1');
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
  # minus { ?s linkml:imports ?p . ?p linkml:imports+ ?o }
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
      nodesAdded.value.push('#'+shrunkSId)
    }
    nodesToFocus.value.push('#'+shrunkSId)
    cyc.value.getElementById(shrunkSId).removeClass('importsMissing')
    cyc.value.getElementById(shrunkSId).addClass('importsAdded')
    let previousRank = cyc.value.getElementById(shrunkSId).data('rank');
    if(cyc.value.getElementById(shrunkOId).length == 0){
      cyc.value.add({group: 'nodes', data: {id: shrunkOId, label: oLabel, rank: previousRank - 1}, classes: ['graph','collapsed','importsMissing']});
      nodesAdded.value.push('#'+shrunkOId)
    }
    else{
      cyc.value.getElementById(shrunkOId).removeClass('importsMissing')
    }
    nodesToFocus.value.push('#'+shrunkOId)
    cyc.value.add({group: 'edges', classes: ['import'], data: {id: shrunkSId + '_' + shrunkOId, source: shrunkSId, target: shrunkOId }});
  });
  importsBindings.on('end', () => {
    console.log(nodesToFocus.value, nodesAdded.value);
    cyc.value.$(nodesToFocus.value.join(', ')).style('opacity', '1');
    cyc.value.$("*").not(nodesToFocus.value.join(', ')).style('opacity', '0.25');
    if(nodesAdded.value.length > 1){
      cyc.value.$(nodesAdded.value.join(', ')).layout(
        {
          name: 'random',
          fit: false,
          boundingBox: {x1: 50, y1: -50, x2: 375, y2: 300},
        }
      ).run();
      nodesAdded.value = [];
    }
  })
  cyc.value.$('#'+node.id()).style('opacity', '1');
  nodesToFocus.value = [];
}

function collapseNodes(evt){ // modified from https://github.com/CamFlow/cytoscape.js-prov/blob/master/cytoscape-prov-core.js
  let node = evt.target;
  if(node.data('removed')!=null){ // the node has already been collapsed
    return;
  }
  var nodes = node.children();
  if(nodes.empty()){
    return;
  }
  var added = new Array();

  cyc.value.startBatch();
  nodes.each(function(n, i){
    n.outgoers().each(function(e, i){
      if(e.target().id()!=undefined){
        e = cyc.value.add([{ group: "edges",  data: { source: node.id(), target: e.target().id(), color: e.data('color'), label: e.data('label')}}]);
        if(!added.includes(e))
          added.push(e);
      }
    });
    n.incomers().each(function(e, i){
      if(e.source().id()!=undefined){
        e = cyc.value.add([{ group: "edges",  data: { source: e.source().id(), target: node.id(), color: e.data('color'), label: e.data('label')}}]);
        if(!added.includes(e))
          added.push(e);
      }
    });
  });
  var removed = nodes.remove();
  node.data('removed', removed);
  node.data('added', added);
  node.edgesTo(node).remove();
  cyc.value.endBatch();
}

function uncollapseNodes(evt){ // modified from https://github.com/CamFlow/cytoscape.js-prov/blob/master/cytoscape-prov-core.js
  let node = evt.target;
  console.log('Asked for collapse!', evt.target);
  cyc.value.startBatch();
  var removed = node.data('removed');
  if(removed==undefined || removed==null){
    return;
  }
  var added = node.data('added');
  removed.restore();
  added.forEach(function(e, i){e.remove()});
  node.edgesTo(node.children()).remove();
  node.children().edgesTo(node).remove();
  node.data('removed', null);
  node.data('added', null);
  cyc.value.endBatch();
}

onMounted(async () => {
  cyc.value = cytoscape({
    container: document.getElementsByClassName('cy-wrapper')[0],
    elements: initialElements.value,
    layout: {name:'preset'},
    style: graphStyle.value
  });
  console.log('Starting!')
  
  var instance = cyc.value.contextMenus({
    menuItems: [
      {
        id: 'showImports',
        content: 'Show graph dependencies',
        tooltipText: 'Show all graphs that this graph depends on',
        selector: '.graph',
        onClickFunction: getGraphImports,
      },
      {
        id: 'showClasses',
        content: 'Show defined classes',
        tooltipText: 'Show all classes defined in this graph',
        selector: '.graph:childless[^removed]',
        onClickFunction: getDefinedClasses,
      },
      {
        id: 'showAllUsedClasses',
        content: 'Show used classes',
        tooltipText: 'Show those classes of which entities instantiated in this graph are types',
        selector: '.graph:childless[^removed]',
        onClickFunction: getAllUsedClasses,
      },
      {
        id: 'showAllEquivalentClasses',
        content: 'Show equivalent classes',
        tooltipText: 'Show those classes defined in this graph that are linked to classes in other graphs',
        selector: '.graph:childless[^removed]',
        onClickFunction: getAllEquivalentClasses,
      },
      {
        id: 'showEquivalents',
        content: 'Show equivalent classes',
        tooltipText: 'Add links to equivalent classes from other graphs',
        selector: '.classDef',
        onClickFunction: getEquivalentClasses
      },
      {
        id: 'collapseNodes',
        content: 'Collapse defined classes',
        tooltipText: 'Display only a single dot for this graph',
        selector: '.graph:parent',
        onClickFunction: collapseNodes
      },
      {
        id: 'uncollapseNodes',
        content: 'Expand defined classes',
        tooltipText: 'Display classes defined by this graph',
        selector: '.graph:childless[removed]',
        onClickFunction: uncollapseNodes
      }
    ]
  });

  cyc.value.on('click', showEntityData);

  cyc.value.on('click', '.usecase', function(evt){
    let node = evt.target;
    let nodeId = node.id();
    for(let newNode of t1graphs[nodeId]){
      cyc.value.add(newNode);
    }
    cyc.value.$('#'+nodeId).style({'opacity': 0.25});
    cyc.value.$('#'+nodeId).style({'events': 'no'});
  })

  cyc.value.on('ready', function(){
    cyc.value.center()
    console.log(cyc.value.elements().boundingBox())
  })

  cyc.value.on('dbltap', function(event){
    // target holds a reference to the originator
    // of the event (core or element)
    var evtTarget = event.target;
    cyc.value.fit()
    if( evtTarget === toRaw(cyc.value) ){
      console.log('tap on background');
    }
    else{
      cyc.value.$("*").not(event.target).style('opacity', '0.5')
    }
  });

  cyc.value.on('mouseover', 'node', function(evt){let node = evt.target; cyc.value.$("#"+node.id()).toggleClass('hovered')})
  cyc.value.on('mouseout', 'node', function(evt){let node = evt.target; cyc.value.$("#"+node.id()).toggleClass('hovered')})
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
        <span class="control-icon control-icon-key" @click="visibleTab='key'" title="Key to symbols">𓃑</span>
        <span class="control-icon control-icon-details" @click="visibleTab='details'" title="Entity details">📖</span>
        <span class="control-icon control-icon-help" @click="visibleTab='help'" title="About the map">ℹ️</span>
      </div>
      <div class="tab-content">
        <template v-if="visibleTab == 'key'">
          <h5>Key to symbols</h5>
          <ul>
            <li>Dots:</li>
            <ul>
              <li>Yellow/green/blue/crimson: Theme 1 graphs (colored by use case)</li>
              <li>Gray: External ontologies (referred to by Theme 1 graphs)</li>
              <li>Red: Class (entity type)</li>
            </ul>
            <li>Arrows:</li>
            <ul>
              <li>Green: Import relationship</li>
              <li>Sky blue: Equivalence relationship</li>
              <li>Light brown: Usage relationship (labeled with number of uses)</li>
            </ul>
            <li>Rectangle: graph or external ontology with classes defined in it</li>
          </ul>
        </template>
        <template v-else-if="visibleTab == 'details'">
          <h5>Entity details</h5>
          <h4>{{ currentEntityDetails['title'] ?? currentEntityDetails['uri'] }}</h4>
          <p style="text-align: center;"><a :href="(prefixes.resolve(rdf.namedNode(currentEntityDetails['uri'] ?? '')) ?? {'value': ''}).value">{{ currentEntityDetails['uri'] }}</a></p>
          <table class="entity-details-table">
            <template v-for="(value, key) in currentEntityDetails">
            <template v-if="!['title','uri'].includes(key)">
            <tr>
              <td style="border-right: 1px solid pink;">{{ mappinglabels[key] }}</td>
              <td style="border-bottom: 1px solid pink;">
                <template v-if="['slots','domain','range'].includes(key)">
                  <template v-for="element in value">
                    <a @click="getEntityData(element.replace(':','_',1), element, [])">{{ element }}</a>
                    <br/>
                  </template>
                </template>
                <template v-else-if="value instanceof Set">
                  <template v-for="element of value">
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
            </template>
            </template>
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
            <p><em><strong>Is there something wrong with the data in this map?</strong></em></p>
            <ul>
              <li>If it relates to a graph you control, then try adding or modifying information about it according to <a href="https://github.com/frink-okn/graph-descriptions/blob/main/README.md">this page</a> and let <a href="mailto:mmorshed@scripps.edu">Mahir Morshed</a> know about the additions or changes.</li>
              <li>If it relates to an external ontology, then just let <a href="mailto:mmorshed@scripps.edu">Mahir Morshed</a> in any case.</li>
            </ul>
            <p>This map was built using Vue 3 and Cytoscape.js.</p>
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
