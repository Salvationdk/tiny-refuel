const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const registry=new Map();
class Node{
 constructor(){this.style={setProperty(){}};this.dataset={};}
 addEventListener(){} querySelector(){return new Node();}querySelectorAll(){return [];}
 attachShadow(){this.shadowRoot=new Node();return this.shadowRoot;}
 dispatchEvent(event){this.lastEvent=event;}
}
const window={customElements:{define:(n,c)=>registry.set(n,c),get:n=>registry.get(n)},navigator:{userAgent:'Desktop'}};
const context={window,customElements:window.customElements,HTMLElement:Node,document:{createElement:n=>new(registry.get(n)||Node)()},CustomEvent:class{constructor(type,o){this.type=type;Object.assign(this,o);}},setInterval(){return 1;},clearInterval(){},setTimeout,clearTimeout,console};
for(const name of ['tiny-refuel-card.js','tiny-refuel-stations.js'])vm.runInNewContext(fs.readFileSync('custom_components/tiny_refuel/frontend/'+name,'utf8'),context);
const Card=registry.get('tiny-refuel-prices-card'),select=Card.selectRows;
for(const type of ['tiny-refuel-card','tiny-refuel-station-card','tiny-refuel-favorites-card'])assert.ok(registry.get(type));
assert.equal(window.customCards.length,4);
const data={stations:[
{id:'a',kind:'fuel',brand:'Q8',name:'Test station',address:'Road A',lat:55,lon:12,prices:{p95:15},current:true},
{id:'b',kind:'fuel',brand:'OK',name:'Station B',lat:56,lon:12,prices:{p95:14},current:true},
{id:'c',kind:'fuel',brand:'Q8',name:'Cached',prices:{p95:1},current:false},
{id:'e',kind:'ev',brand:'Q8',name:'Charger',prices:{kwh:3},current:true}]};
assert.equal(select(data,{},null).map(r=>r.id).join(','),'b,a,c');
assert.equal(select(data,{mode:'favorites',favorites:['a']},null).map(r=>r.id).join(','),'a');
assert.equal(select(data,{mode:'station',station_id:'e',fuel:'all'},null).map(r=>r.id).join(','),'e');
assert.equal(select(data,{radius_km:10},null).length,0);
const hass={states:{'person.driver':{state:'home',attributes:{latitude:55,longitude:12}}}};
assert.equal(select(data,{location_entity:'person.driver',radius_km:10},hass).map(r=>r.id).join(','),'a');
assert.equal(select(data,{brands:['Q8']},null,'Road A').length,1);
assert.equal(select(data,{fuel:'all'},null,'','all','price').length,4);
const editor=new(registry.get('tiny-refuel-stations-editor'))();editor.setConfig({type:'custom:tiny-refuel-favorites-card',favorites:['a']});editor._change('favorites',['a','b']);
assert.equal(editor.lastEvent.type,'config-changed');assert.equal(editor.lastEvent.detail.config.favorites.join(','),'a,b');
(async()=>{
 let calls=0;const connected={states:{},connection:{},callApi:async()=>{calls++;return data;}};
 const a=new Card(),b=new Card();a.hass=connected;b.hass=connected;
 await new Promise(r=>setTimeout(r,0));assert.equal(calls,1,'Cards share requests');
 assert.ok(a._station({...data.stations[0],distance:null}).includes('/static/logos/logo-q8.svg'));
 assert.ok(!a._station({...data.stations[0],distance:null}).includes('undefined'));
 assert.throws(()=>a.setConfig({fuel:'unknown'}));
 const large=new Card();large.setConfig({type:'custom:tiny-refuel-prices-card',limit:100});
 large._data={stations:Array.from({length:101},(_,i)=>({...data.stations[0],id:String(i)}))};large._render();
 assert.ok(!large.shadowRoot.innerHTML.includes('data-more>Vis flere'));
 assert.ok(large.shadowRoot.innerHTML.includes('Viser 100 resultater.'));

 console.log('PASS: station filters, favorites, stale ordering, request reuse and saved editor choices');
})().catch(error=>{console.error(error);process.exitCode=1;});
