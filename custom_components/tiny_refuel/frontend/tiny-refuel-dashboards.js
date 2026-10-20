/* Additional dashboards. Existing station and vehicle cards keep their own config. */
(function(window){
 'use strict';
 function register(){
  if(customElements.get('tiny-refuel-vehicles-card'))return;
  const base=customElements.get('tiny-refuel-prices-card').dashboardTools;
  const theme=customElements.get('tiny-refuel-card').stationTheme;
  const {esc,fmt,stamp,valid,origin,distance,coords,fuels}=base;
  const definitions=[
   ['tiny-refuel-vehicles-card','vehicles','Mine køretøjer','Fælles køretøjer med nærmeste steder og beregnede omkostninger'],
   ['tiny-refuel-comparison-card','comparison','Prissammenligning','Sammenlign pris, afstand og omkostning for ét køretøj'],
   ['tiny-refuel-vehicle-details-card','details','Køretøjsoplysninger','Model, årgang, variant, kapacitet og tilgængelig kontrolstatus'],
   ['tiny-refuel-status-card','status','Datastatus','Kilder, seneste hentning, lokal historik, kort og katalogstatus']];
  const modes=Object.fromEntries(definitions.map(d=>['custom:'+d[0],d[1]]));
  const titles=Object.fromEntries(definitions.map(d=>[d[1],d[2]]));
  const fuelFields={benzin:['p95','p100'],diesel:['diesel'],el:['kwh'],hybrid:['p95','p100'],plug_in_hybrid:['p95','p100','kwh']};
  const fuelNames={benzin:'Benzin',diesel:'Diesel',el:'El',hybrid:'Hybrid uden stik',plug_in_hybrid:'Plug-in-hybrid'};
  const statuses={needs_review:'Mangler kontrol',source_supported:'Understøttet af en kilde',verified:'Kontrolleret',user_entered:'Indtastet af brugeren'};
  const dataRequests=new WeakMap();
  function dashboard(hass,force=false){
   const key=hass.connection||hass,old=dataRequests.get(key);
   if(old&&(old.pending||!force&&Date.now()-old.at<30000))return old.promise;
   const record={at:Date.now(),pending:true};
   record.promise=hass.callApi('GET','tiny_refuel/dashboard').then(data=>{
    if(!data||!Array.isArray(data.vehicles)||!Array.isArray(data.sources))throw Error('Ugyldige data');
    record.pending=false;return data;
   }).catch(error=>{dataRequests.delete(key);throw error;});
   dataRequests.set(key,record);return record.promise;
  }
  function vehicles(data,config){return (Array.isArray(config.biler)?config.biler:(data.vehicles||[])).map((car,i)=>({...car,id:car.id||'local-'+i}));}
  function capacity(car,field){const value=field==='kwh'?car.batteri_kwh:car.tank_liters;return valid(value)?value:null;}
  function vehicleName(car){return car.navn||[car.mærke,car.model].filter(Boolean).join(' ')||'Køretøj';}
  function comparisons(data,config,hass,car,field,sort='price'){
   if(!car||!(fuelFields[car.brændstof]||[]).includes(field))return [];
   const selected={...config,mode:'prices',fuel:field,location_entity:config.location_entity||car.location_entity};
   return base.selectRows(data,selected,hass,'',field,sort).filter(row=>row.current&&valid(row.prices[field])).map(row=>{
    const size=capacity(car,field);return {...row,full_cost:size===null?null:row.prices[field]*size};
   });
  }
  const css=`
   .td-list{display:grid;gap:12px}.td-car{border:1px solid rgba(0,229,255,.25);border-radius:14px;padding:13px;background:linear-gradient(135deg,rgba(0,229,255,.05),rgba(185,103,255,.035));min-width:0}
   .td-heading{display:flex;gap:10px;align-items:center;margin-bottom:8px}.td-heading ha-icon{color:var(--primary-color);--mdc-icon-size:25px}.td-heading strong{font-size:15px;overflow-wrap:anywhere}.td-meta{font-size:11px;color:var(--secondary-text-color);line-height:1.6}
   .td-facts{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.td-fact{border-radius:10px;padding:8px 10px;background:rgba(127,127,127,.07);font-size:11px;color:var(--secondary-text-color)}.td-fact strong{display:block;color:var(--primary-text-color);font-size:18px;font-variant-numeric:tabular-nums}.td-label{font-size:10px;color:var(--secondary-text-color)}
   .td-near{border-top:1px solid var(--divider-color);padding-top:9px;margin-top:9px;font-size:12px;line-height:1.6}.td-near a{color:var(--primary-color);text-decoration:none}.td-cost{font-size:18px;font-weight:700;color:var(--primary-color);font-variant-numeric:tabular-nums}.td-cost small{font-size:11px;font-weight:400;color:var(--secondary-text-color)}
   .td-table{width:100%;border-collapse:collapse;font-size:12px}.td-table th,.td-table td{padding:10px 4px;border-bottom:1px solid var(--divider-color);text-align:right;vertical-align:top;font-variant-numeric:tabular-nums}.td-table th:first-child,.td-table td:first-child{text-align:left}.td-table th{font-size:10px;color:var(--secondary-text-color);font-weight:400}.td-table td:first-child{max-width:180px;overflow-wrap:anywhere}.td-table small{display:block;color:var(--secondary-text-color);font-size:10px}.td-table a{color:var(--primary-color);text-decoration:none}.td-table tr:first-child .td-cost{font-size:17px}
   .td-status{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--divider-color);border-radius:18px;padding:4px 8px;font-size:10px;white-space:normal}.td-status.good{color:var(--success-color,#4caf50)}.td-status.warn{color:var(--warning-color,#ffb340)}.td-status.neutral{color:var(--secondary-text-color)}
   .td-source{display:flex;gap:8px;align-items:center;justify-content:space-between;padding:9px 0;border-bottom:1px solid var(--divider-color);font-size:12px}.td-source>div{min-width:0;overflow-wrap:anywhere}.td-source small{display:block;font-size:10px;color:var(--secondary-text-color);margin-top:4px}.td-section{margin-top:16px}.td-section h4{font-size:13px;margin:8px 0}.td-section summary{cursor:pointer;font-size:12px}.td-kv{display:grid;grid-template-columns:minmax(90px,1fr) minmax(0,2fr);gap:7px;font-size:12px;line-height:1.5}.td-kv dt{color:var(--secondary-text-color)}.td-kv dd{margin:0;overflow-wrap:anywhere}.td-kv a{color:var(--primary-color)}
   .td-tariffs{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}.td-tariff{padding:10px;border:1px solid var(--divider-color);border-radius:12px;font-size:12px;line-height:1.5}.td-tariff strong{font-size:17px;color:var(--primary-color)}
   @container tiny-refuel (max-width:400px){.td-table{font-size:11px}.td-table th,.td-table td{padding:8px 3px}.td-table .td-cost{font-size:14px}.td-table small{font-size:9px}.td-kv{grid-template-columns:90px minmax(0,1fr)}}`;
  function navigation(row,config){
   if(!coords(row))return '';
   const ll=row.lat+','+row.lon;
   return config.navigation==='waze'?'https://waze.com/ul?ll='+ll+'&navigate=yes':'https://www.google.com/maps/dir/?api=1&destination='+encodeURIComponent(ll);
  }
  function vehicleHeader(car){return '<div class="td-heading"><ha-icon icon="'+(car.brændstof==='el'?'mdi:car-electric':'mdi:car')+'"></ha-icon><strong>'+esc(vehicleName(car))+'</strong></div><div class="td-meta">'+esc([car.mærke,car.model,car.aargang,car.variant].filter(Boolean).join(' · '))+'</div>';}
  function vehicleFacts(car){return '<div class="td-facts"><div class="td-fact">Drivmiddel<strong>'+esc(fuelNames[car.brændstof]||'Ikke oplyst')+'</strong></div>'+[['tank_liters','Tank','L'],['batteri_kwh','Batteri','kWh']].filter(([k])=>valid(car[k])).map(([k,label,unit])=>'<div class="td-fact">'+label+'<strong>'+fmt(car[k])+' '+unit+'</strong></div>').join('')+'</div>';}
  function tariffSection(data,config){
   const rows=(data.tariffs||[]).filter(r=>!config.brands||!config.brands.length||config.brands.some(b=>b.toLowerCase()===String(r.brand).toLowerCase()));
   if(!rows.length)return '<section class="td-section"><h4>Generelle selskabstakster</h4><div class="ts-sub">Ingen generelle takster i de indlæste data.</div></section>';
   return '<section class="td-section"><h4>Generelle selskabstakster</h4><div class="ts-sub">Standard- og fra-priser. Ikke en lokal stationspris. Abonnement, tidspunkt og gebyrer kan ændre din pris.</div><div class="td-tariffs">'+rows.map(r=>'<div class="td-tariff"><b>'+esc(r.brand)+'</b><div>'+esc(r.name||r.kind||'Standardtakst')+'</div><strong>'+fmt(r.kwh)+'</strong> kr/kWh'+(!r.current?'<div class="td-status warn">Gemt takst · ikke bekræftet</div>':'')+'</div>').join('')+'</div></section>';
  }
  class ChargingCard extends base.StationCard{
   static getStubConfig(){return {fuel:'kwh',sort:'distance',limit:8,show_tariffs:true};}
   setConfig(config){super.setConfig({...config,fuel:'kwh',title:config.title||'Opladning'});}
   _render(){
    super._render();
    const root=this.shadowRoot;
    if(!root||!this._config)return;
    const field=root.querySelector('[data-fuel]');if(field){field.value='kwh';field.disabled=true;}
    const subtitle=root.querySelector('.ts-sub');if(subtitle)subtitle.textContent='Lokale ladesteder · pris og afstand';
    if(this._data&&this._config.show_tariffs!==false){
     const host=document.createElement('div');host.className='td-charge-extra';host.innerHTML='<style>'+css+'</style>'+tariffSection(this._data,this._config);
     const box=root.querySelector('.trf');if(box)box.append(host);
    }
   }
  }
  class DashboardCard extends base.StationCard{
   static getConfigElement(){return document.createElement('tiny-refuel-dashboard-editor');}
   static getStubConfig(){return {compact:false,limit:6};}
   setConfig(config){this._kind=modes[config.type]||'vehicles';super.setConfig(config);}
   set hass(hass){
    this._hass=hass;theme.apply(this,hass);
    const cars=vehicles(this._data||{},this._config);
    const key=JSON.stringify([cars.map(c=>origin(hass,this._config.location_entity||c.location_entity)),hass.themes&&hass.themes.darkMode]);
    if(this._signature!==key){this._signature=key;this._render();}this._load();
   }
   async _load(force=false){
    if(!this._hass||!this._hass.callApi||this._loading||!force&&this._fetched&&Date.now()-this._fetched<30000)return;
    this._loading=true;
    try{
     const [data,stations]=await Promise.all([dashboard(this._hass,force),['vehicles','comparison'].includes(this._kind)?base.snapshot(this._hass,force):Promise.resolve({})]);
     this._data={...data,...stations};this._error=null;this._fetched=Date.now();
    }catch(error){this._error='Oplysningerne kunne ikke hentes. Prøv igen om lidt.';}
    finally{this._loading=false;if(this._connected)this._render();}
   }
   _selected(){
    const rows=vehicles(this._data||{},this._config),id=this._vehicleChoice===undefined?this._config.vehicle_id:this._vehicleChoice;
    return id?rows.filter(r=>r.id===id):rows;
   }
   _overview(car){
    const location=origin(this._hass,this._config.location_entity||car.location_entity);
    let html='<article class="td-car">'+vehicleHeader(car)+vehicleFacts(car);
    if(!location)html+='<div class="ts-notice">Position mangler. Vælg en positionsenhed for nærmeste steder.</div>';
    else for(const field of fuelFields[car.brændstof]||[]){
     const config={...this._config,mode:'prices',location_entity:this._config.location_entity||car.location_entity};
     const rows=base.selectRows(this._data,config,this._hass,'',field,'distance').filter(r=>r.current&&r.distance!==null);
     const row=rows[0];
     html+='<div class="td-near"><div class="td-label">Nærmeste '+esc(fuels[field])+'</div>';
     if(!row){html+='Ingen aktuelle steder med de valgte filtre.</div>';continue;}
     const cost=valid(row.prices[field])&&capacity(car,field)!==null?row.prices[field]*capacity(car,field):null;
     const nav=navigation(row,this._config);
     html+='<b>'+esc(row.name)+'</b> · '+fmt(row.distance)+' km<div class="td-meta">'+esc(row.address||row.brand)+'</div>'+(valid(row.prices[field])?fmt(row.prices[field])+' kr/'+(field==='kwh'?'kWh':'L'):'Lokal pris ikke oplyst')+(cost!==null?'<div class="td-cost">'+fmt(cost)+' kr. <small>for hele kapaciteten</small></div>':'')+(nav?'<a target="_blank" rel="noopener noreferrer" href="'+esc(nav)+'">Find vej ↗</a>':'')+'</div>';
    }
    return html+'</article>';
   }
   _comparison(){
    const all=vehicles(this._data||{},this._config),selected=this._selected(),car=selected[0];
    let html='<div class="ts-tools"><label>Køretøj<select data-vehicle>'+all.map(v=>'<option value="'+esc(v.id)+'"'+(car&&car.id===v.id?' selected':'')+'>'+esc(vehicleName(v))+'</option>').join('')+'</select></label>';
    if(!car)return '<div class="ts-empty"><strong>Vælg et fælles køretøj</strong>Tilføj eller vælg et køretøj i opsætningen.</div>';
    const allowed=fuelFields[car.brændstof]||[],field=allowed.includes(this._comparisonField)?this._comparisonField:allowed.includes(this._config.fuel)?this._config.fuel:allowed[0];
    html+='<label>Drivmiddel<select data-comparison-field>'+allowed.map(f=>'<option value="'+f+'"'+(field===f?' selected':'')+'>'+fuels[f]+'</option>').join('')+'</select></label></div>';
    if(!field)return html+'<div class="ts-notice">Køretøjets drivmiddel er ikke oplyst.</div>';
    const size=capacity(car,field),location=origin(this._hass,this._config.location_entity||car.location_entity);
    if(size===null)html+='<div class="ts-notice">Kapacitet mangler. Enhedspriser kan sammenlignes, men totalomkostningen kan ikke beregnes.</div>';
    if(!location)html+='<div class="ts-sub">Position mangler. Afstand er ikke tilgængelig.</div>';
    const rows=comparisons(this._data,this._config,this._hass,car,field,this._comparisonSort||this._config.sort||'price');
    const priced=rows.map(r=>r.full_cost).filter(v=>v!==null),minimum=priced.length?Math.min(...priced):null;
    html+='<label>Sortering<select data-comparison-sort><option value="price"'+((this._comparisonSort||this._config.sort||'price')==='price'?' selected':'')+'>Laveste pris</option><option value="distance"'+((this._comparisonSort||this._config.sort)==='distance'?' selected':'')+'>Nærmeste</option></select></label><div class="ts-count">'+rows.length+' aktuelle priser'+(size!==null?' · '+fmt(size)+' '+(field==='kwh'?'kWh':'L'):'')+'</div>';
    if(!rows.length)return html+'<div class="ts-empty">Ingen aktuelle priser matcher køretøj og filtre.</div>';
    html+='<table class="td-table"><thead><tr><th>Station / afstand</th><th>kr/'+(field==='kwh'?'kWh':'L')+'</th><th>Hel kapacitet (kr.)</th><th>Merpris (kr.)</th></tr></thead><tbody>';
    for(const row of rows.slice(0,this._config.limit||6)){
     const nav=navigation(row,this._config);
     html+='<tr><td>'+(nav?'<a href="'+esc(nav)+'" target="_blank" rel="noopener noreferrer">':'')+esc(row.name)+(nav?'</a>':'')+'<small>'+esc(row.address||row.brand)+(row.distance!==null?' · '+fmt(row.distance)+' km':'')+'</small></td><td>'+fmt(row.prices[field])+'</td><td class="td-cost">'+(row.full_cost===null?'–':fmt(row.full_cost))+'</td><td>'+(row.full_cost===null?'–':'+'+fmt(Math.max(0,row.full_cost-minimum)))+'</td></tr>';
    }
    return html+'</tbody></table><div class="ts-sub">Pris × indtastet kapacitet. Beregningen viser en hel tank eller batterikapacitet. Ladetab og gebyrer er ikke medregnet. Merpris måles mod den billigste pris i det valgte udvalg.</div>';
   }
   _details(car){
    const entries=[['Køretøjstype',car.koeretoejstype],['Årgang',car.aargang],['Variant',car.variant],['Kontrolstatus',statuses[car.capacity_status]||'Ikke oplyst'],['Kontroldato',car.capacity_checked_at]];
    const scope=car.capacity_scope||{};
    if(scope.production_start||scope.production_end)entries.push(['Kildens produktion',(scope.production_start||'?')+'–'+(scope.production_end||'?')]);
    const links=(Array.isArray(car.capacity_source_urls)?car.capacity_source_urls:[]).filter(u=>typeof u==='string'&&/^https?:\/\//i.test(u));
    return '<article class="td-car">'+vehicleHeader(car)+vehicleFacts(car)+'<dl class="td-kv">'+entries.map(([k,v])=>'<dt>'+k+'</dt><dd>'+esc(v||'Ikke oplyst')+'</dd>').join('')+(links.length?'<dt>Kilder</dt><dd>'+links.map((u,i)=>'<a target="_blank" rel="noopener noreferrer" href="'+esc(u)+'">Kilde '+(i+1)+' ↗</a>').join('<br>')+'</dd>':'')+'</dl><div class="ts-sub">Oplysningerne kommer fra det gemte køretøj. Kontrollér, at årgang og variant passer til kapaciteten.</div></article>';
   }
   _status(){
    const data=this._data,sources=data.sources||[],good=sources.filter(s=>s.status==='ok'),bad=sources.filter(s=>s.status!=='ok');
    let html='<div class="td-facts"><div class="td-fact">Kilder i orden<strong>'+good.length+'</strong></div><div class="td-fact">Øvrige kilder<strong>'+bad.length+'</strong></div><div class="td-fact">Indlæste katalogtyper<strong>'+((data.catalogs&&data.catalogs.loaded_types)||[]).length+'</strong></div></div><div class="td-meta">Seneste hentning: '+esc(stamp(data.updated))+'<br>Seneste forsøg: '+esc(stamp(data.last_attempt))+'</div>';
    if(data.last_error)html+='<div class="ts-notice" role="alert">'+esc(data.last_error)+'</div>';
    if(data.refreshing)html+='<div class="ts-notice">Henter data'+(data.progress&&data.progress.provider?' · '+esc(data.progress.provider):'')+'…</div>';
    if(!sources.length)html+='<div class="ts-empty">Der er endnu ingen kildeoplysninger. Hent data for at se status.</div>';
    const sourceRow=s=>'<div class="td-source"><div>'+esc(s.name)+'<small>Senest i orden: '+esc(stamp(s.last_success))+'</small>'+((s.error||s.last_error)?'<small>'+esc(s.error||s.last_error)+'</small>':'')+'</div><span class="td-status '+(s.status==='ok'?'good':'warn')+'">'+esc(({ok:'I orden',stale:'Gemt kopi',error:'Fejl',not_collected:'Ikke hentet',cached:'Gemt kopi'})[s.status]||s.status||'Ukendt')+'</span></div>';
    html+=bad.map(sourceRow).join('');
    if(good.length)html+='<details class="td-section"'+(this._config.show_ok_sources?' open':'')+'><summary>Kilder i orden ('+good.length+')</summary>'+good.map(sourceRow).join('')+'</details>';
    const messages=[...(data.errors||[]),...(data.benefit_errors||[])];
    if(messages.length)html+='<details class="td-section"><summary>Øvrige meldinger ('+messages.length+')</summary>'+messages.map(row=>'<div class="td-source">'+esc(typeof row==='string'?row:Object.entries(row).map(([k,v])=>k+': '+(typeof v==='object'?JSON.stringify(v):String(v))).join(' · '))+'</div>').join('')+'</details>';
    const catalog=data.catalogs||{},rows=catalog.catalogs||{};
    html+='<section class="td-section"><h4>Kataloger</h4>'+Object.entries(rows).map(([type,meta])=>'<div class="td-source"><div>'+esc(type)+'<small>'+esc(meta.models||0)+' modeller · '+esc(meta.version||'Medfølgende katalog')+'</small></div><span class="td-status '+(meta.stale?'warn':'good')+'">'+(meta.stale?'Gemt kopi':'Tilgængeligt')+'</span></div>').join('')+(!Object.keys(rows).length?'<div class="td-meta">Ingen katalogtyper indlæst endnu.</div>':'')+'<div class="ts-sub">Katalogstatus beskriver filernes tilgængelighed. Den godkender ikke kapaciteterne.</div></section>';
    html+='<section class="td-section"><h4>Historik og kort</h4><div class="td-meta">Historik: '+((data.history&&data.history.days)?data.history.days+' dage':'slået fra')+'<br>Stationsmarkører: '+(data.map&&data.map.enabled?(data.map.count||0)+' vist':'slået fra')+'</div>';
    if(data.history&&data.history.error)html+='<div class="ts-notice">'+esc(data.history.error)+'</div>';
    if(data.map&&data.map.enabled&&!data.map.origin_available)html+='<div class="ts-notice">Kortets position er ikke tilgængelig.</div>';
    if(data.map&&data.map.matched>data.map.limit)html+='<div class="ts-sub">Markørgrænsen viser '+data.map.limit+' af '+data.map.matched+' matchende stationer.</div>';
    html+='</section><button class="ts-btn" data-collect'+(data.refreshing||this._starting?' disabled':'')+'>Hent nye data</button>';
    if(this._collectError)html+='<div class="ts-notice" role="alert">'+esc(this._collectError)+'</div>';
    return html;
   }
   _render(){
    if(!this.shadowRoot)return;
    const kind=this._kind||'vehicles',c=this._config||{};
    let content='';
    if(this._error)content+='<div class="ts-notice" role="alert">'+esc(this._error)+'</div>';
    if(!this._data)content+='<div class="ts-empty">'+(this._loading?'Henter oplysninger…':'Tilføj Tiny Refuel for at se oplysninger.')+'</div>';
    else if(kind==='status')content+=this._status();
    else if(kind==='comparison')content+=this._comparison();
    else{
     const rows=this._selected();
     content+='<div class="td-list">'+rows.map(car=>kind==='details'?this._details(car):this._overview(car)).join('')+'</div>';
     if(!rows.length)content+='<div class="ts-empty"><strong>Intet fælles køretøj valgt</strong>Tilføj køretøjer under Tiny Refuels integrationsindstillinger, eller vælg et eksisterende køretøj i editoren.</div>';
     if(kind==='vehicles'&&rows.length)content+='<div class="ts-sub">Omkostningen er for hele den indtastede kapacitet. Aktuelt tankindhold, batteriniveau, ladetab og gebyrer indgår ikke.</div>';
    }
    this.shadowRoot.innerHTML='<style>'+theme.css+base.css+css+'</style><ha-card><div class="trf'+(c.compact?' trf-compact':'')+'"><div class="trf-titlebar"><div class="trf-title">'+esc(c.title||titles[kind])+'</div><button class="ts-btn" data-reload aria-label="Opdatér visning">↻</button></div><div class="trf-rule"></div><div class="ts-sub">'+({vehicles:'Dine køretøjer · relevante steder og priser',comparison:'Samme drivmiddel · sammenlignelige priser',details:'Det gemte køretøj · variant og kapacitet',status:'Overblik over dine datakilder'})[kind]+'</div>'+content+'</div></ha-card>';
    const root=this.shadowRoot;
    root.querySelector('[data-reload]').onclick=()=>this._load(true);
    const pick=root.querySelector('[data-vehicle]');if(pick)pick.onchange=e=>{this._vehicleChoice=e.target.value;this._comparisonField=null;this._render();};
    const field=root.querySelector('[data-comparison-field]');if(field)field.onchange=e=>{this._comparisonField=e.target.value;this._render();};
    const sort=root.querySelector('[data-comparison-sort]');if(sort)sort.onchange=e=>{this._comparisonSort=e.target.value;this._render();};
    const collect=root.querySelector('[data-collect]');if(collect)collect.onclick=async()=>{
     this._starting=true;this._collectError=null;this._render();
     try{await this._hass.callService('tiny_refuel','refresh',{});await this._load(true);}
     catch(error){this._collectError='Datahentningen kunne ikke startes.';}
     finally{this._starting=false;this._render();}
    };
   }
  }
  class DashboardEditor extends HTMLElement{
   constructor(){super();this.attachShadow({mode:'open'});this._config={};}
   setConfig(config){this._config={...config};this._render();}
   set hass(hass){this._hass=hass;theme.apply(this,hass);if(!this._rendered)this._render();const picker=this.shadowRoot.querySelector('[data-location]');if(picker)picker.hass=hass;this._load();}
   async _load(){
    if(!this._hass||!this._hass.callApi||this._data||this._loading)return;
    this._loading=true;
    try{this._data=await dashboard(this._hass);this._error=null;}
    catch(error){this._error='Køretøjslisten kunne ikke hentes. Åbn editoren igen for at prøve igen.';}
    finally{this._loading=false;this._render();}
   }
   _change(key,value){
    const config={...this._config};if(value===undefined||value==='')delete config[key];else config[key]=value;
    this._config=config;this.dispatchEvent(new CustomEvent('config-changed',{detail:{config},bubbles:true,composed:true}));
   }
   _render(){
    this._rendered=true;const c=this._config,kind=modes[c.type]||'vehicles';
    const cars=vehicles(this._data||{},c);
    let html='<style>'+theme.editorCss+base.css+'.trfe label{display:grid;gap:5px;margin:10px 0}.td-check{display:flex!important;align-items:center}.td-check input{width:18px;min-height:18px}</style><div class="trfe"><h4>'+titles[kind]+'</h4><div class="trfe-hint">Valgfrit ekstra kort. Opsætningerne i dine andre kort bevares.</div><label>Overskrift<input data-key="title" type="text" value="'+esc(c.title||titles[kind])+'"></label>';
    if(kind!=='status'){
     html+='<label>Fælles køretøj<select data-key="vehicle_id"><option value="">'+(kind==='comparison'?'Første fælles køretøj':'Alle fælles køretøjer')+'</option>'+cars.map(car=>'<option value="'+esc(car.id)+'"'+(car.id===c.vehicle_id?' selected':'')+'>'+esc(vehicleName(car))+'</option>').join('')+'</select></label>';
     if(!cars.length)html+='<div class="ts-notice">Tilføj køretøjer i Tiny Refuels integrationsindstillinger. Derefter kan de vælges her.</div>';
     if(c.vehicle_id&&!cars.some(car=>car.id===c.vehicle_id))html+='<div class="ts-notice">Det valgte køretøj findes ikke længere. Vælg et andet.</div>';
    }
    if(kind==='comparison'){
     const chosen=cars.find(car=>car.id===c.vehicle_id)||cars[0],fields=chosen?fuelFields[chosen.brændstof]||[]:Object.keys(fuels);
     html+='<label>Drivmiddel<select data-key="fuel">'+fields.map(f=>'<option value="'+f+'"'+(f===c.fuel?' selected':'')+'>'+fuels[f]+'</option>').join('')+'</select></label><label>Sortering<select data-key="sort"><option value="price"'+(c.sort!=='distance'?' selected':'')+'>Laveste pris</option><option value="distance"'+(c.sort==='distance'?' selected':'')+'>Nærmeste</option></select></label><label>Antal viste stationer<input data-key="limit" type="number" min="1" max="100" value="'+(c.limit||6)+'"></label>';
    }
    if(kind==='comparison'||kind==='vehicles'){
     html+='<details class="trfe-section"><summary>Afstand og selskaber</summary><div class="trfe-section-body"><label>Positionsenhed (erstatter køretøjets position)'+(this._hass?'<ha-entity-picker data-location></ha-entity-picker>':'<span>Indlæser Home Assistant…</span>')+'</label><label>Radius i km (0 = alle)<input data-key="radius_km" type="number" min="0" value="'+(c.radius_km||0)+'"></label><div class="trfe-hint">Afstand er i luftlinje. Uden position kan priser stadig sammenlignes, når radius er 0.</div>';
     html+='<div class="trfe-hint">Ingen selskaber valgt betyder alle.</div>'+theme.brands.map(b=>'<label class="td-check"><input type="checkbox" data-brand="'+esc(b.brand)+'"'+((c.brands||[]).some(x=>x.toLowerCase()===b.brand.toLowerCase())?' checked':'')+'>'+esc(b.brand)+'</label>').join('')+'</div></details><label>Navigation<select data-key="navigation"><option value="google"'+(c.navigation!=='waze'?' selected':'')+'>Google Maps</option><option value="waze"'+(c.navigation==='waze'?' selected':'')+'>Waze</option></select></label>';
    }
    if(kind==='status')html+='<label class="td-check"><input data-key="show_ok_sources" type="checkbox"'+(c.show_ok_sources?' checked':'')+'>Vis kilder i orden som udgangspunkt</label><div class="trfe-hint">Kortet viser kilder, kataloger, historik og kortmarkører. Hent nye data kan startes fra kortet.</div>';
    html+='<label class="td-check"><input data-key="compact" type="checkbox"'+(c.compact?' checked':'')+'>Kompakt visning</label>';
    if(this._error)html+='<div class="ts-notice" role="alert">'+esc(this._error)+'</div>';
    this.shadowRoot.innerHTML=html+'</div>';
    this.shadowRoot.querySelectorAll('[data-key]').forEach(el=>el.onchange=()=>{
     let value=el.type==='checkbox'?el.checked:el.type==='number'?Number(el.value):el.value;
     if(el.type==='number'&&(!Number.isFinite(value)||value<0))return;
     if(el.dataset.key==='limit')value=Math.min(100,Math.max(1,Math.round(value)));
     if(el.dataset.key==='vehicle_id'){delete this._config.fuel;}
     this._change(el.dataset.key,value);
    });
    const picker=this.shadowRoot.querySelector('[data-location]');if(picker){picker.hass=this._hass;picker.value=c.location_entity||'';picker.includeDomains=['person','device_tracker','zone'];picker.addEventListener('value-changed',e=>{e.stopPropagation();this._change('location_entity',e.detail.value);});}
    this.shadowRoot.querySelectorAll('[data-brand]').forEach(el=>el.onchange=()=>{const set=new Set(this._config.brands||[]);el.checked?set.add(el.dataset.brand):set.delete(el.dataset.brand);this._change('brands',[...set]);});
   }
  }
  class ChargingEditor extends base.StationEditor{
   _render(){
    super._render();const root=this.shadowRoot,field=root.querySelector('[data-key="fuel"]');
    if(field){field.value='kwh';field.disabled=true;}
    const heading=root.querySelector('h4');if(heading)heading.textContent='Opladning';
    const box=root.querySelector('.trfe');if(box){const label=document.createElement('label');label.className='ts-check';label.innerHTML='<input data-tariffs type="checkbox"'+(this._config.show_tariffs!==false?' checked':'')+'>Vis generelle selskabstakster separat';box.append(label);const input=root.querySelector('[data-tariffs]');if(input)input.onchange=()=>this._change('show_tariffs',input.checked);}
   }
  }
  ChargingCard.getConfigElement=()=>document.createElement('tiny-refuel-charging-editor');
  customElements.define('tiny-refuel-dashboard-editor',DashboardEditor);
  customElements.define('tiny-refuel-charging-editor',ChargingEditor);
  for(const [type,kind,name,description] of definitions){
   class Card extends DashboardCard{}
   customElements.define(type,Card);window.customCards.push({type,name:'Tiny Refuel · '+name,description,preview:true});
  }
  customElements.define('tiny-refuel-charging-card',ChargingCard);
  window.customCards.push({type:'tiny-refuel-charging-card',name:'Tiny Refuel · Opladning',description:'Lokale ladesteder og særskilte generelle selskabstakster',preview:true});
  customElements.get('tiny-refuel-comparison-card').calculateRows=comparisons;
 }
 if(customElements.get('tiny-refuel-prices-card'))register();else customElements.whenDefined('tiny-refuel-prices-card').then(register);
})(window);
