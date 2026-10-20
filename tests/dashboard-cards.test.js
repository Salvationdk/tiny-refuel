const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const registry=new Map();
class Node{
 constructor(){this.style={setProperty(){}};this.dataset={};}
 addEventListener(){}querySelector(){return new Node();}querySelectorAll(){return [];}append(){}
 attachShadow(){this.shadowRoot=new Node();return this.shadowRoot;}
 dispatchEvent(event){this.lastEvent=event;}
}
const window={customElements:{define:(n,c)=>registry.set(n,c),get:n=>registry.get(n)},navigator:{userAgent:'Desktop'}};
const context={window,customElements:window.customElements,HTMLElement:Node,document:{createElement:n=>new(registry.get(n)||Node)()},CustomEvent:class{constructor(type,o){this.type=type;Object.assign(this,o);}},setInterval(){return 1;},clearInterval(){},setTimeout,clearTimeout,console};
for(const name of ['tiny-refuel-card.js','tiny-refuel-stations.js','tiny-refuel-dashboards.js'])vm.runInNewContext(fs.readFileSync('custom_components/tiny_refuel/frontend/'+name,'utf8'),context);
assert.equal(window.customCards.length,9);
assert.ok(window.customCards.every(card=>card.preview===false), "All Tiny Refuel entries keep the card picker compact");
for(const name of ["tiny-refuel-card","tiny-refuel-prices-card","tiny-refuel-vehicles-card","tiny-refuel-charging-card"])assert.equal(typeof registry.get(name).getConfigElement,"function", "Selected cards retain their editor");
for(const name of ['vehicles','comparison','vehicle-details','status','charging'])assert.ok(registry.get('tiny-refuel-'+name+'-card'));
const Compare=registry.get('tiny-refuel-comparison-card');
const car={id:'car',navn:'Testbil',brændstof:'benzin',tank_liters:35,location_entity:'person.driver'};
const data={vehicles:[car],sources:[],stations:[
{id:'a',kind:'fuel',brand:'Q8',name:'Near',address:'A',lat:55,lon:12,prices:{p95:15},current:true},
{id:'b',kind:'fuel',brand:'OK',name:'Cheap',address:'B',lat:56,lon:12,prices:{p95:14},current:true},
{id:'c',kind:'fuel',brand:'Q8',name:'Cached',prices:{p95:1},current:false},
{id:'e',kind:'ev',brand:'Q8',name:'Charger',prices:{kwh:3},current:true}]};
const hass={states:{'person.driver':{state:'home',attributes:{latitude:55,longitude:12}}}};
const calc=Compare.calculateRows;
assert.equal(calc(data,{},hass,car,'p95')[0].full_cost,490);
assert.equal(calc(data,{},hass,car,'p95','distance')[0].id,'a');
assert.equal(calc(data,{},hass,car,'kwh').length,0,'petrol capacity cannot become an electric cost');
assert.equal(calc(data,{},hass,{...car,tank_liters:null},'p95')[0].full_cost,null);
assert.equal(calc(data,{radius_km:10},hass,car,'p95').length,1);
assert.equal(calc(data,{radius_km:10},null,car,'p95').length,0);
const ionity={...data,stations:[{...data.stations[3],brand:'IONITY'}]};
assert.equal(calc(ionity,{brands:['Ionity']},hass,{...car,brændstof:'el',batteri_kwh:45},'kwh')[0].full_cost,135);

const compare=new Compare();compare.setConfig({type:'custom:tiny-refuel-comparison-card'});compare._data=data;compare._hass=hass;compare._render();
assert.ok(compare.shadowRoot.innerHTML.includes('490,00'));assert.ok(!compare.shadowRoot.innerHTML.includes('Cached'));
compare._config.vehicle_id='removed';compare._render();assert.ok(compare.shadowRoot.innerHTML.includes('Vælg et køretøj'));
const Details=registry.get('tiny-refuel-vehicle-details-card'),details=new Details();details.setConfig({type:'custom:tiny-refuel-vehicle-details-card'});
details._data={...data,vehicles:[{...car,capacity_status:'needs_review',capacity_source_urls:['javascript:alert(1)','https://example.com/spec'],aargang:2015}]};details._render();
assert.ok(details.shadowRoot.innerHTML.includes('Mangler kontrol'));assert.ok(!details.shadowRoot.innerHTML.includes('javascript:'));
assert.ok(details.shadowRoot.innerHTML.includes('https://example.com/spec'));
const Status=registry.get('tiny-refuel-status-card'),status=new Status();status.setConfig({type:'custom:tiny-refuel-status-card'});status._data={...data,last_error:'<bad>',history:{days:90},map:{enabled:false}};status._render();
assert.ok(status.shadowRoot.innerHTML.includes('&lt;bad&gt;'));assert.ok(status.shadowRoot.innerHTML.includes('90 dage'));
const charging=new(registry.get('tiny-refuel-charging-card'))();charging.setConfig({type:'custom:tiny-refuel-charging-card',fuel:'p95'});assert.equal(charging._config.fuel,'kwh');
const editor=new(registry.get('tiny-refuel-dashboard-editor'))();editor.setConfig({type:'custom:tiny-refuel-comparison-card'});editor._change('vehicle_id','car');assert.equal(editor.lastEvent.detail.config.vehicle_id,'car');
console.log('PASS: nine card registrations, vehicle costs, current local prices, radius, missing capacity, safe evidence, status and electric-only charging');
(async()=>{
 const {collectVehicles,withDashboardVehicles,vehicles}=Compare.vehicleTools;
 const oldCar={navn:'Familiebil',mærke:'Volkswagen',model:'up!',tank_liters:35,brændstof:'benzin',location_entity:'person.driver'};
 const oldCard={type:'custom:tiny-refuel-card',biler:[oldCar,null]};
 const panel={views:[{sections:[{cards:[{type:'vertical-stack',cards:[oldCard,{type:'conditional',card:oldCard}]}]}]}]};
 const before=JSON.stringify(panel);
 const found=collectVehicles(panel);assert.equal(found.length,1);assert.equal(found[0].tank_liters,35);
 assert.equal(found[0].id,collectVehicles({cards:[oldCard]})[0].id);
 assert.equal(collectVehicles({cards:[oldCard,{...oldCard,biler:[{...oldCar,tank_liters:40}]}]}).length,2);
 assert.equal(JSON.stringify(panel),before,'reading never changes existing configs');
 let calls=0;const messages=[];
 const api={callWS:async message=>{calls++;messages.push(message);return panel;},callApi:async()=>({vehicles:[],sources:[]})};
 window.location={pathname:'/lovelace/test'};
 const config={type:'custom:tiny-refuel-vehicle-details-card'};
 const [a,b]=await Promise.all([withDashboardVehicles(api,{vehicles:[]},config),withDashboardVehicles(api,{vehicles:[]},config)]);
 assert.equal(calls,1,'concurrent card/editor requests share one dashboard read');
 assert.equal(messages[0].url_path,null);assert.equal(vehicles(a,config)[0].navn,'Familiebil');
 assert.equal(vehicles(b,{biler:[]}).length,0,'an explicit empty local list stays empty');
 assert.equal(vehicles({vehicles:[car],dashboard_vehicles:found},config)[0].id,'car','shared vehicles take priority');
 await withDashboardVehicles(api,{vehicles:[car]},config);assert.equal(calls,1);
 await withDashboardVehicles(api,{vehicles:[]},{type:'custom:tiny-refuel-status-card'});assert.equal(calls,1);
 window.location.pathname='/dashboard-family/test';await withDashboardVehicles(api,{vehicles:[]},config);
 assert.equal(calls,2);assert.equal(messages[1].url_path,'dashboard-family');
 const live=new Details();live.setConfig(config);live._hass=api;await live._load(true);live._render();
 assert.ok(live.shadowRoot.innerHTML.includes('Familiebil'));assert.equal(live._selected()[0].tank_liters,35);
 const ed=new(registry.get('tiny-refuel-dashboard-editor'))();ed.setConfig(config);ed._hass=api;await ed._load();
 assert.ok(ed.shadowRoot.innerHTML.includes('Familiebil'));assert.equal(ed._config.biler,undefined);
 const failed=await withDashboardVehicles({callWS:async()=>{throw Error('unavailable');}},{vehicles:[]},config);
 assert.equal(failed.dashboard_vehicle_error,true);assert.equal(vehicles(failed,config).length,0);
 assert.equal((await withDashboardVehicles({}, {vehicles:[]},config)).dashboard_vehicles.length,0);
 console.log('PASS: existing dashboard vehicles, nested cards, stable IDs, distinct capacities, shared priority, read-only fallback, editor/runtime agreement and request caching');
})().catch(error=>{console.error(error);process.exitCode=1;});
