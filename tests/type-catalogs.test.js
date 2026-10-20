const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'custom_components/tiny_refuel/frontend/tiny-refuel-card.js'), 'utf8');
const requests = [];
const registrations = new Map();
class Element { addEventListener() {} querySelectorAll(){return [];} querySelector(){return null;} }
const window = {customElements:{define:(n,t)=>registrations.set(n,t), get:n=>registrations.get(n)}, navigator:{userAgent:'test'}};
const context={window,customElements:window.customElements,HTMLElement:Element,console,Map,Set,WeakMap,Promise,Date,setTimeout,clearTimeout,
 fetch:async url=>({ok:true,json:async()=>({logos:{VW:'svg'}})})};
vm.createContext(context);
vm.runInContext(source.replace('}(window);','window.typeTest={typedCatalogSelection,loadTypedVehicleCatalog,mergeTypedCatalogs};}(window);'),context);
const api=window.typeTest;
const car={vehicle_type:'personbil',brands:[{'mærke':'VW',modeller:[{model:'up!',tank_l:35,vehicle_types:['personbil']}]}]};
const van={vehicle_type:'varebil',brands:[{'mærke':'VW',modeller:[{model:'up!',tank_l:35,vehicle_types:['varebil']}]}]};
(async()=>{
 let render=0;
 const owner={_config:{biler:[{koeretoejstype:'personbil'}]},_render(){render++;},_hass:{callApi:async(method,url)=>{requests.push(url);return car;}}};
 assert.equal(api.loadTypedVehicleCatalog(owner,api.typedCatalogSelection(owner)),true);
 await new Promise(resolve=>setTimeout(resolve,0));
 assert.equal(requests.length,1);assert.equal(requests[0],'tiny_refuel/catalog/personbil');assert.equal(render,1);
 api.loadTypedVehicleCatalog(owner,['personbil']);await new Promise(resolve=>setTimeout(resolve,0));assert.equal(requests.length,1);
 assert.equal(owner._katalog.brands[0].modeller[0].tank_l,35);
 const joined=api.mergeTypedCatalogs([car,van],{});
 assert.equal(joined.brands.length,1);assert.equal(joined.brands[0].modeller.length,1);
 assert.deepEqual(Array.from(joined.brands[0].modeller[0].vehicle_types).sort(),['personbil','varebil']);
 assert.equal(car.brands[0].modeller[0].vehicle_types.length,1,'merge must not mutate original catalog rows');
 assert.equal(api.typedCatalogSelection({_config:{katalog_url:'/local/custom.json',biler:[{koeretoejstype:'personbil'}]}}).length,0);
 assert.deepEqual(Array.from(api.typedCatalogSelection({_config:{biler:[{koeretoejstype:'varevogn'},{koeretoejstype:'lastbil'}]}})),['lastbil','varebil']);
 // Race: a response for a previously selected type must not overwrite the latest selection.
 let release;
 const racing={_config:{},_render(){},_hass:{callApi:(method,url)=>url.endsWith('motorcykel')?new Promise(r=>release=r):Promise.resolve({...van,vehicle_type:'bus'})}};
 api.loadTypedVehicleCatalog(racing,['motorcykel']);api.loadTypedVehicleCatalog(racing,['bus']);
 await new Promise(resolve=>setTimeout(resolve,0));release({...car,vehicle_type:'motorcykel'});
 await new Promise(resolve=>setTimeout(resolve,0));assert.equal(racing._katalog.catalog_downloads[0].type,'bus');
 console.log('PASS: type-only downloads, reuse, multi-type merge, custom URLs, aliases and stale-response race');
})().catch(e=>{console.error(e);process.exitCode=1;});
