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
compare._config.vehicle_id='removed';compare._render();assert.ok(compare.shadowRoot.innerHTML.includes('Vælg et fælles køretøj'));
const Details=registry.get('tiny-refuel-vehicle-details-card'),details=new Details();details.setConfig({type:'custom:tiny-refuel-vehicle-details-card'});
details._data={...data,vehicles:[{...car,capacity_status:'needs_review',capacity_source_urls:['javascript:alert(1)','https://example.com/spec'],aargang:2015}]};details._render();
assert.ok(details.shadowRoot.innerHTML.includes('Mangler kontrol'));assert.ok(!details.shadowRoot.innerHTML.includes('javascript:'));
assert.ok(details.shadowRoot.innerHTML.includes('https://example.com/spec'));
const Status=registry.get('tiny-refuel-status-card'),status=new Status();status.setConfig({type:'custom:tiny-refuel-status-card'});status._data={...data,last_error:'<bad>',history:{days:90},map:{enabled:false}};status._render();
assert.ok(status.shadowRoot.innerHTML.includes('&lt;bad&gt;'));assert.ok(status.shadowRoot.innerHTML.includes('90 dage'));
const charging=new(registry.get('tiny-refuel-charging-card'))();charging.setConfig({type:'custom:tiny-refuel-charging-card',fuel:'p95'});assert.equal(charging._config.fuel,'kwh');
const editor=new(registry.get('tiny-refuel-dashboard-editor'))();editor.setConfig({type:'custom:tiny-refuel-comparison-card'});editor._change('vehicle_id','car');assert.equal(editor.lastEvent.detail.config.vehicle_id,'car');
console.log('PASS: nine card registrations, vehicle costs, current local prices, radius, missing capacity, safe evidence, status and electric-only charging');
