/* Optional station cards. The existing vehicle card is unchanged. */
(function (window) {
  'use strict';
  function register() {
    if (customElements.get('tiny-refuel-prices-card')) return;
    const theme = customElements.get('tiny-refuel-card').stationTheme;
    const fuels = {p95:'Benzin 95',p100:'Benzin 100',diesel:'Diesel',kwh:'El'};
    const titles = {prices:'Prisoversigt',station:'Min station',favorites:'Mine favoritter'};
    const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const fmt = value => Number(value).toLocaleString('da-DK',{minimumFractionDigits:2,maximumFractionDigits:2});
    const valid = value => typeof value === 'number' && Number.isFinite(value) && value > 0;
    const coords = row => typeof row.lat==='number' && typeof row.lon==='number' && Number.isFinite(row.lat) && Number.isFinite(row.lon) && Math.abs(row.lat)<=90 && Math.abs(row.lon)<=180 && (row.lat!==0 || row.lon!==0);
    const stamp = value => value && Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString('da-DK') : 'Tidspunkt ukendt';
    const requests = new WeakMap();
    function snapshot(hass, force=false) {
      const key=hass.connection || hass;
      const old=requests.get(key);
      if (old && (!force && Date.now()-old.at<30000 || old.pending)) return old.promise;
      const record={at:Date.now(),pending:true};
      record.promise=hass.callApi('GET','tiny_refuel/stations').then(data=>{
        if (!data || !Array.isArray(data.stations)) throw Error('Ugyldige stationsdata');
        record.pending=false; return data;
      }).catch(error=>{requests.delete(key);throw error;});
      requests.set(key,record);return record.promise;
    }
    function distance(a,b) {
      const rad=n=>n*Math.PI/180;
      const x=Math.sin(rad(b.lat-a.lat)/2)**2+Math.cos(rad(a.lat))*Math.cos(rad(b.lat))*Math.sin(rad(b.lon-a.lon)/2)**2;
      return 12742*Math.asin(Math.min(1,Math.sqrt(x)));
    }
    function origin(hass,entity) {
      if (!hass || !entity) return null;
      const state=hass.states && hass.states[entity];
      if (!state || ['unknown','unavailable'].includes(state.state)) return null;
      const row={lat:state.attributes.latitude,lon:state.attributes.longitude};
      return coords(row)?row:null;
    }
    function selectRows(data,config,hass,search='',field=config.fuel || 'p95',sort=config.sort || 'price') {
      const location=origin(hass,config.location_entity);
      let rows=(data.stations||[]).map(row=>({...row,distance:location && coords(row)?distance(location,row):null}));
      const selected=config.favorites||[];
      rows=rows.filter(row=>{
        if (config.mode==='station' && row.id!==config.station_id) return false;
        if (config.mode==='favorites' && !selected.includes(row.id)) return false;
        if (config.brands && config.brands.length && !config.brands.includes(row.brand)) return false;
        if (config.radius_km>0 && (row.distance===null || row.distance>config.radius_km)) return false;
        if (search && ![row.brand,row.name,row.address].join(' ').toLocaleLowerCase('da').includes(search.toLocaleLowerCase('da'))) return false;
        return field==='all' || valid(row.prices[field]) || (row.kind==='ev' && field==='kwh');
      });
      rows.sort((a,b)=>{
        if (sort==='name') return (a.brand+' '+a.name).localeCompare(b.brand+' '+b.name,'da');
        const av=sort==='distance'?a.distance:(a.current && valid(a.prices[field])?a.prices[field]:null);
        const bv=sort==='distance'?b.distance:(b.current && valid(b.prices[field])?b.prices[field]:null);
        return (av===null?Infinity:av)-(bv===null?Infinity:bv) || (a.brand+' '+a.name).localeCompare(b.brand+' '+b.name,'da');
      });
      return rows;
    }
    const extraCSS=`
      :host{display:block}*{box-sizing:border-box}.trf{overflow:hidden}.trf-title{text-transform:none;letter-spacing:.2px;font-size:17px}
      .ts-sub{font-size:12px;color:var(--secondary-text-color);line-height:1.5;margin:8px 0 14px}
      .ts-tools{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}.ts-search{grid-column:1/-1}
      input,select,button{font:inherit;color:var(--primary-text-color)}input,select{min-height:40px;background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:10px;padding:8px 10px;width:100%;min-width:0}
      label{font-size:11px;color:var(--secondary-text-color);display:grid;gap:4px}button{cursor:pointer}.ts-btn{border:1px solid var(--divider-color);background:transparent;border-radius:10px;padding:8px 12px;min-height:36px}.ts-btn:hover{background:rgba(0,229,255,.08)}
      button:focus-visible,a:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
      .ts-count{font-size:11px;color:var(--secondary-text-color);margin:10px 0}.ts-list{display:grid;gap:10px}
      .ts-station{border:1px solid rgba(0,229,255,.28);border-radius:14px;background:linear-gradient(135deg,rgba(0,229,255,.055),rgba(185,103,255,.035));padding:12px}
      .ts-top{display:flex;align-items:center;gap:10px}.ts-logo{height:24px;max-width:72px;object-fit:contain}.ts-name{flex:1;min-width:0;font-size:13px;font-weight:600;overflow-wrap:anywhere}.ts-address{font-size:11px;color:var(--secondary-text-color);line-height:1.5;margin:5px 0;overflow-wrap:anywhere}
      .ts-favorite{border:0;background:transparent;font-size:22px;color:var(--secondary-text-color);min-width:40px;min-height:40px}.ts-favorite[aria-pressed=true]{color:var(--primary-color)}
      .ts-prices{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.ts-price{padding:7px 10px;border-radius:10px;background:rgba(127,127,127,.07);min-width:86px}.ts-price span{display:block;font-size:10px;color:var(--secondary-text-color)}.ts-price strong{font-size:21px;font-variant-numeric:tabular-nums;color:var(--primary-color);font-weight:700}.ts-price small{font-size:10px;color:var(--secondary-text-color);margin-left:4px}
      .ts-foot{display:flex;flex-wrap:wrap;align-items:center;gap:8px;font-size:10px;color:var(--secondary-text-color);margin-top:8px}.ts-foot a{color:var(--primary-color);text-decoration:none}.ts-foot time{flex:1}.ts-notice{padding:10px 12px;border-radius:10px;background:rgba(255,179,64,.09);font-size:12px;line-height:1.5;margin:10px 0}.ts-empty{text-align:center;padding:28px 12px;color:var(--secondary-text-color);font-size:13px;line-height:1.6}.ts-empty strong{display:block;color:var(--primary-text-color);margin-bottom:5px}
      .ts-history{margin-top:12px;border-top:1px solid var(--divider-color);padding-top:10px}.ts-history summary{cursor:pointer;font-size:12px}.ts-history svg{display:block;width:100%;height:130px;margin-top:8px}.ts-history table{width:100%;font-size:11px;border-collapse:collapse}.ts-history td{padding:5px;border-bottom:1px solid var(--divider-color)}.ts-history td:last-child{text-align:right}.ts-history-tools{display:flex;gap:8px;margin-top:10px}.ts-history-tools label{flex:1}.ts-value-range{display:flex;justify-content:space-between;font-size:11px;color:var(--secondary-text-color)}
      .trf-compact .ts-station{padding:9px}.trf-compact .ts-price strong{font-size:17px}.trf-compact .ts-sub{margin-bottom:8px}
      @media(prefers-reduced-motion:no-preference){.ts-btn,.ts-favorite{transition:background .15s,color .15s}}`;

    class StationCard extends HTMLElement {
      constructor(){super();this.attachShadow({mode:'open'});this._config={};this._data=null;this._histories=new Map();this._loading=false;this._connected=false;this._search='';}
      static getConfigElement(){return document.createElement('tiny-refuel-stations-editor');}
      static getStubConfig(){return {fuel:'p95',limit:8,sort:'price'};}
      setConfig(config){
        if (!config || typeof config!=='object') throw Error('Kortets opsætning mangler');
        const modes={'custom:tiny-refuel-prices-card':'prices','custom:tiny-refuel-station-card':'station','custom:tiny-refuel-favorites-card':'favorites'};
        if (config.fuel && !Object.hasOwn(fuels,config.fuel) && config.fuel!=='all') throw Error('Ukendt drivmiddel');
        if(config.sort && !['price','distance','name'].includes(config.sort))throw Error('Ukendt sortering');
        for(const key of ['brands','favorites'])if(config[key]!==undefined && (!Array.isArray(config[key]) || config[key].some(v=>typeof v!=='string')))throw Error('Ugyldigt stationsvalg');
        if(config.limit!==undefined && (!Number.isInteger(config.limit)||config.limit<1||config.limit>100))throw Error('Antallet skal være 1–100');
        if(config.radius_km!==undefined && (typeof config.radius_km!=='number'||!Number.isFinite(config.radius_km)||config.radius_km<0))throw Error('Radius skal være et positivt tal eller 0');
        this._config={fuel:'p95',limit:8,sort:config.fuel==='all'?'name':'price',...config,mode:modes[config.type]||'prices'};
        this._fuel=this._config.fuel;this._sort=this._config.sort;this._shown=this._config.limit;
        this._render();this._load();
      }
      set hass(hass){this._hass=hass;theme.apply(this,hass);const signature=JSON.stringify([origin(hass,this._config.location_entity),hass.themes&&hass.themes.darkMode]);if(signature!==this._signature){this._signature=signature;this._render();}this._load();}
      getCardSize(){return Math.min(12,2+2*(this._config.mode==='station'?1:this._config.limit||8));}
      connectedCallback(){this._connected=true;this._load();this._timer=setInterval(()=>this._load(true),60000);}
      disconnectedCallback(){this._connected=false;clearInterval(this._timer);}
      async _load(force=false){
        if (!this._hass || !this._hass.callApi || this._loading || (!force && this._fetched && Date.now()-this._fetched<30000)) return;
        this._loading=true;
        try{this._data=await snapshot(this._hass,force);this._error=null;this._fetched=Date.now();}
        catch(error){this._error='Stationsdata kunne ikke hentes. Prøv igen om lidt.';}
        finally{this._loading=false;if(this._connected)this._render();}
      }
      _navigation(row){
        if (!coords(row)) return '';
        const ll=row.lat+','+row.lon;
        return this._config.navigation==='waze'?'https://waze.com/ul?ll='+ll+'&navigate=yes':'https://www.google.com/maps/dir/?api=1&destination='+encodeURIComponent(ll);
      }
      _station(row){
        const brand=theme.brands.find(b=>b.brand.toLowerCase()===row.brand.toLowerCase());
        const fields=this._fuel==='all'?Object.keys(fuels).filter(f=>valid(row.prices[f])):[this._fuel];
        const current=row.current && !this._error;
        const prices=fields.map(field=>'<div class="ts-price"><span>'+esc(fuels[field])+'</span><strong>'+ (valid(row.prices[field])?fmt(row.prices[field]):'–')+'</strong><small>kr/'+(field==='kwh'?'kWh':'L')+'</small></div>').join('');
        const nav=this._navigation(row);
        return '<article class="ts-station" data-station="'+esc(row.id)+'"><div class="ts-top">'+(brand?'<img class="ts-logo" alt="'+esc(row.brand)+'" src="/tiny_refuel/static/logos/'+esc(brand.img)+'">':'')+'<div class="ts-name">'+esc(row.name)+'</div></div><div class="ts-address">'+esc(row.address||row.brand)+(row.charger_kind?' · '+esc(row.charger_kind):'')+(row.distance!==null?' · '+fmt(row.distance)+' km':'')+'</div>'+
          (!current?'<div class="ts-notice">'+(row.ambiguous?'Modstridende priser i datakilden.':'Gemt pris · ikke bekræftet ved seneste hentning.')+'</div>':'')+
          '<div class="ts-prices">'+(prices||'<span class="ts-address">Ingen offentliggjort lokal pris</span>')+'</div><div class="ts-foot"><time>Hentet '+esc(stamp(row.updated))+'</time>'+(nav?'<a href="'+esc(nav)+'" target="_blank" rel="noopener noreferrer">Find vej ↗</a>':'')+'</div>'+this._history(row)+'</article>';
      }
      _history(row){
        if (this._config.mode!=='station') return '';
        const field=this._historyField || (this._fuel==='all'?Object.keys(row.prices)[0]||'p95':this._fuel);
        const days=this._historyDays||7,key=row.id+':'+field+':'+days;
        const result=this._histories.get(key);
        const opts=Object.keys(fuels).filter(f=>valid(row.prices[f]));if(!opts.includes(field))opts.push(field);
        let content='Åbn for at hente registrerede prisændringer.';
        if (result && result.error) content=result.error;
        else if(result){
          if(!result.enabled)content='Historik er slået fra i integrationens indstillinger.';
          else if(!result.points.length)content='Ingen registrerede priser i perioden endnu. Historikken starter ved aktivering.';
          else {
            const points=result.points,values=points.map(p=>p.value),lo=Math.min(...values),hi=Math.max(...values),span=hi-lo||1;
            const start=Date.now()-result.days*86400000,end=Date.now();
            const x=p=>Math.max(0,Math.min(600,(Date.parse(p.at)-start)/(end-start)*600));
            const y=p=>100-(p.value-lo)/span*80;
            let path='M '+x(points[0])+' '+y(points[0]);
            for(let i=1;i<points.length;i++)path+=' H '+x(points[i])+' V '+y(points[i]);
            // End at the last observation, never extend a price to the present as a live fact.
            content='<svg viewBox="0 0 600 120" role="img" aria-label="Registrerede prisændringer"><path d="'+path+'" fill="none" stroke="var(--primary-color)" stroke-width="3" vector-effect="non-scaling-stroke"/>'+points.map(p=>'<circle cx="'+x(p)+'" cy="'+y(p)+'" r="3" fill="var(--primary-color)"/>').join('')+'</svg><div class="ts-value-range"><span>Lavest '+fmt(lo)+'</span><span>Højest '+fmt(hi)+'</span></div><table><tbody>'+points.slice(-12).reverse().map(p=>'<tr><td>'+esc(stamp(p.baseline?p.observed_at:p.at))+(p.baseline?' · tidligere observation (udgangspunkt)':'')+'</td><td>'+fmt(p.value)+' kr/'+(field==='kwh'?'kWh':'L')+'</td></tr>').join('')+'</tbody></table>'+(result.truncated?'<p>Perioden indeholder flere ændringer end visningsgrænsen. Vælg en kortere periode.</p>':'');
          }
        }
        return '<details class="ts-history"'+(this._historyOpen?' open':'')+'><summary>Prishistorik</summary><div class="ts-history-tools"><label>Drivmiddel<select data-history-field>'+opts.map(f=>'<option value="'+f+'"'+(f===field?' selected':'')+'>'+fuels[f]+'</option>').join('')+'</select></label><label>Periode<select data-history-days>'+[1,7,30,90,365].map(d=>'<option value="'+d+'"'+(d===days?' selected':'')+'>'+d+' dage</option>').join('')+'</select></label></div><div class="ts-sub">'+content+'</div><div class="ts-address">Viser observationer og prisændringer, ikke en garanti for prisen mellem hentninger. Opbevaring: '+(this._data.history_days||0)+' dage.</div></details>';
      }
      async _loadHistory(){
        const row=(this._data.stations||[]).find(r=>r.id===this._config.station_id);if(!row)return;
        const field=this._historyField || (this._fuel==='all'?Object.keys(row.prices)[0]||'p95':this._fuel),days=this._historyDays||7,key=row.id+':'+field+':'+days;
        if(this._histories.has(key)&&!this._histories.get(key).retry)return;
        this._histories.set(key,{error:'Henter historik…'});this._render();
        try{const data=await this._hass.callApi('GET','tiny_refuel/history/'+row.id+'?field='+field+'&days='+days);this._histories.set(key,data);}
        catch(error){this._histories.set(key,{error:'Historikken kunne ikke hentes. Tryk på opdateringsknappen for at prøve igen.'});}
        this._render();
      }
      _render(){
        if(!this.shadowRoot)return;
        const c=this._config,data=this._data||{stations:[]};
        const rows=selectRows(data,c,this._hass,this._search,this._fuel,this._sort),shown=rows.slice(0,Math.max(1,Math.min(100,this._shown||8)));
        const location=origin(this._hass,c.location_entity);
        const label=c.title||titles[c.mode]||titles.prices;
        let html='<style>'+theme.css+extraCSS+'</style><ha-card><div class="trf'+(c.compact?' trf-compact':'')+'"><div class="trf-titlebar"><div class="trf-title">'+esc(label)+'</div><button class="ts-btn" data-reload aria-label="Opdatér visning">↻</button></div><div class="trf-rule"></div><div class="ts-sub">'+(c.mode==='station'?'Din station · priser og historik':c.mode==='favorites'?'Dine valgte steder · samlet ét sted':'Lokale priser · uden køretøjsopsætning')+'</div>';
        if(c.mode!=='station') html+='<div class="ts-tools"><label>Drivmiddel<select data-fuel>'+['all',...Object.keys(fuels)].map(f=>'<option value="'+f+'"'+(f===this._fuel?' selected':'')+'>'+(fuels[f]||'Alle priser')+'</option>').join('')+'</select></label><label>Sortering<select data-sort>'+[['price','Laveste pris'],['distance','Nærmeste'],['name','Selskab og navn']].map(([v,l])=>'<option value="'+v+'"'+(v===this._sort?' selected':'')+'>'+l+'</option>').join('')+'</select></label><label class="ts-search">Find station<input data-search type="search" placeholder="Selskab, station eller adresse" value="'+esc(this._search)+'"></label></div>';
        if(this._error)html+='<div class="ts-notice" role="alert">'+esc(this._error)+'</div>';
        if(data.last_error)html+='<div class="ts-notice">Seneste datahentning fejlede. Priserne nedenfor er gemte oplysninger.</div>';
        if(data.history_error)html+='<div class="ts-notice">'+esc(data.history_error)+'</div>';
        if((c.radius_km>0||this._sort==='distance')&&!location)html+='<div class="ts-notice">Vælg en tilgængelig positionsenhed i kortets opsætning for afstand og radius.</div>';
        if(c.mode!=='station'&&this._fuel==='all'&&this._sort==='price')html+='<div class="ts-address">Vælg ét drivmiddel for at sortere efter pris. Liter og kWh sammenlignes ikke.</div>';
        html+='<div class="ts-count" aria-live="polite">'+rows.length+' resultater'+(location?' · afstand i luftlinje':'')+'</div><div class="ts-list">'+shown.map(r=>this._station(r)).join('')+'</div>';
        if(!shown.length)html+='<div class="ts-empty"><strong>'+(this._loading?'Henter stationer…':c.mode==='favorites'?'Dine favoritter starter her':c.mode==='station'?(c.station_id?'Stationen mangler i de indlæste data':'Vælg din station'):'Ingen stationer matcher')+'</strong>'+(c.mode==='favorites'?'Vælg favoritter i kortets visuelle editor.':c.mode==='station'?'Åbn kortets visuelle editor og vælg en station.':'Prøv et andet drivmiddel eller en bredere afgrænsning.')+'</div>';
        if(rows.length>shown.length)html+=shown.length<100?'<button class="ts-btn" data-more>Vis flere</button>':'<div class="ts-sub">Viser 100 resultater. Søg eller afgræns med selskab og radius for at finde flere.</div>';
        html+='<div class="ts-sub">Hentet '+esc(stamp(data.updated))+' · '+(data.refreshing?'Datahentning i gang':'Generelle selskabstakster er udeladt')+'</div></div></ha-card>';
        const root=this.shadowRoot;root.innerHTML=html;
        root.querySelector('[data-reload]').onclick=()=>{this._fetched=0;this._histories.clear();this._load(true);};
        const fuel=root.querySelector('[data-fuel]');if(fuel)fuel.onchange=e=>{this._fuel=e.target.value;this._render();};
        const sort=root.querySelector('[data-sort]');if(sort)sort.onchange=e=>{this._sort=e.target.value;this._render();};
        const search=root.querySelector('[data-search]');if(search)search.oninput=e=>{const p=e.target.selectionStart;this._search=e.target.value;this._render();const next=root.querySelector('[data-search]');next.focus();try{next.setSelectionRange(p,p);}catch(error){}};
        const more=root.querySelector('[data-more]');if(more)more.onclick=()=>{this._shown=Math.min(100,(this._shown||8)+8);this._render();};
        const history=root.querySelector('.ts-history');if(history)history.ontoggle=()=>{this._historyOpen=history.open;if(history.open)this._loadHistory();};
        const hf=root.querySelector('[data-history-field]');if(hf)hf.onchange=e=>{this._historyField=e.target.value;this._loadHistory();};
        const hd=root.querySelector('[data-history-days]');if(hd)hd.onchange=e=>{this._historyDays=Number(e.target.value);this._loadHistory();};
      }
    }
    class StationEditor extends HTMLElement {
      constructor(){super();this.attachShadow({mode:'open'});this._config={};this._filter='';}
      setConfig(config){this._config={...config};this._render();}
      set hass(hass){this._hass=hass;theme.apply(this,hass);if(!this._rendered)this._render();const picker=this.shadowRoot.querySelector('[data-location]');if(picker)picker.hass=hass;this._load();}
      async _load(){
        if(this._loading||this._data||!this._hass||!this._hass.callApi)return;
        this._loading=true;
        try{this._data=await snapshot(this._hass);this._error=null;}
        catch(error){this._error='Stationslisten kunne ikke hentes. Åbn editoren igen for at prøve igen.';}
        finally{this._loading=false;this._render();}
      }
      _change(key,value){
        const config={...this._config};if(value===undefined||value==='')delete config[key];else config[key]=value;
        this._config=config;
        this.dispatchEvent(new CustomEvent('config-changed',{detail:{config},bubbles:true,composed:true}));
      }
      _render(){
        this._rendered=true;
        const c=this._config,mode=c.type==='custom:tiny-refuel-station-card'?'station':c.type==='custom:tiny-refuel-favorites-card'?'favorites':'prices';
        const rows=(this._data&&this._data.stations||[]).slice().sort((a,b)=>(a.brand+' '+a.name).localeCompare(b.brand+' '+b.name,'da'));
        const search=this._filter.toLocaleLowerCase('da');
        const matching=rows.filter(r=>[r.brand,r.name,r.address].join(' ').toLocaleLowerCase('da').includes(search));
        const selected=rows.find(r=>r.id===c.station_id),shown=matching.slice(0,100);
        if(selected&&!shown.includes(selected))shown.unshift(selected);
        const input=(key,label,type='text',value=c[key]||'')=>'<label>'+label+'<input data-key="'+key+'" type="'+type+'" value="'+esc(value)+'"'+(type==='number'?' min="0"':'')+'></label>';
        let html='<style>'+theme.editorCss+extraCSS+'.trfe label{display:grid;gap:5px;margin:9px 0}.ts-check{display:flex!important;align-items:center;gap:8px!important}.ts-check input{width:18px;min-height:18px}.ts-editor-choices{max-height:320px;overflow:auto;padding:0 8px;border:1px solid var(--divider-color);border-radius:10px}.ts-editor-choices label{border-bottom:1px solid var(--divider-color);padding:8px 0;line-height:1.5}.ts-editor-choices small{display:block;color:var(--secondary-text-color)}</style><div class="trfe"><h4>'+titles[mode]+'</h4><p class="trfe-hint">Et selvstændigt kort med stationspriser. Intet køretøj er nødvendigt.</p>'+input('title','Overskrift','text',c.title||titles[mode]);
        html+='<label>Drivmiddel<select data-key="fuel">'+['all',...Object.keys(fuels)].map(f=>'<option value="'+f+'"'+((c.fuel||'p95')===f?' selected':'')+'>'+(fuels[f]||'Alle priser')+'</option>').join('')+'</select></label>';
        if(mode!=='station') html+='<label>Sortering<select data-key="sort">'+[['price','Laveste pris'],['distance','Nærmeste'],['name','Selskab og navn']].map(([v,l])=>'<option value="'+v+'"'+((c.sort||(c.fuel==='all'?'name':'price'))===v?' selected':'')+'>'+l+'</option>').join('')+'</select></label>'+input('limit','Antal viste stationer (1–100)','number',c.limit||8);
        if(mode==='station'||mode==='favorites'){
          html+='<h4>'+ (mode==='station'?'Vælg station':'Vælg favoritter')+'</h4><label>Søg i stationer<input data-filter type="search" placeholder="Selskab, station eller adresse" value="'+esc(this._filter)+'"></label>';
          if(mode==='station') html+='<label>Station<select data-key="station_id"><option value="">Vælg en station</option>'+shown.map(r=>'<option value="'+r.id+'"'+(c.station_id===r.id?' selected':'')+'>'+esc(r.brand+' · '+r.name+(r.address&&r.address!==r.name?' · '+r.address:'')+(r.charger_kind?' · '+r.charger_kind:''))+'</option>').join('')+'</select></label>';
          else html+='<div class="ts-editor-choices">'+shown.map(r=>'<label class="ts-check"><input data-favorite="'+r.id+'" type="checkbox"'+((c.favorites||[]).includes(r.id)?' checked':'')+'><span>'+esc(r.brand+' · '+r.name)+'<small>'+esc(r.address||'')+(r.charger_kind?' · '+esc(r.charger_kind):'')+'</small></span></label>').join('')+'</div><div class="trfe-hint">'+(c.favorites||[]).length+' favoritter valgt. Valgene gemmes sammen med kortet.</div>';
          html+='<div class="trfe-hint">'+matching.length+' matcher · viser op til 100. Søg for at finde flere.</div>';
        }
        if(mode==='prices'){
          const brands=[...new Set(rows.map(r=>r.brand))].sort();
          html+='<details class="trfe-section"><summary>Selskaber</summary><div class="trfe-section-body"><p class="trfe-hint">Ingen afkrydsninger betyder alle selskaber.</p>'+brands.map(b=>'<label class="ts-check"><input data-brand="'+esc(b)+'" type="checkbox"'+((c.brands||[]).includes(b)?' checked':'')+'>'+esc(b)+'</label>').join('')+'</div></details>';
        }
        html+='<details class="trfe-section"><summary>Afstand og udseende</summary><div class="trfe-section-body"><label>Positionsenhed'+(this._hass?'<ha-entity-picker data-location></ha-entity-picker>':'<span>Indlæser Home Assistant…</span>')+'</label>'+input('radius_km','Radius i km (0 = alle)','number',c.radius_km||0)+'<div class="trfe-hint">Afstand er i luftlinje og kræver en positionsenhed med koordinater.</div><label>Navigation<select data-key="navigation"><option value="google"'+(c.navigation!=='waze'?' selected':'')+'>Google Maps</option><option value="waze"'+(c.navigation==='waze'?' selected':'')+'>Waze</option></select></label><label class="ts-check"><input data-key="compact" type="checkbox"'+(c.compact?' checked':'')+'>Kompakt visning</label></div></details>';
        if(mode==='station')html+='<p class="trfe-hint">Stationskortet har prishistorik. Opbevaringsperioden vælges under Tiny Refuels integrationsindstillinger.</p>';
        if(this._error)html+='<div role="alert" class="ts-notice">'+esc(this._error)+'</div>';
        this.shadowRoot.innerHTML=html+'</div>';
        const picker=this.shadowRoot.querySelector('[data-location]');if(picker){picker.hass=this._hass;picker.value=c.location_entity||'';picker.includeDomains=['person','device_tracker','zone'];picker.allowCustomEntity=false;
        picker.addEventListener('value-changed',e=>{e.stopPropagation();this._change('location_entity',e.detail.value);});}
        this.shadowRoot.querySelectorAll('[data-key]').forEach(el=>el.onchange=()=>{
          let value=el.type==='checkbox'?el.checked:el.type==='number'?Number(el.value):el.value;
          if(el.type==='number' && (!Number.isFinite(value)||value<0))return;
          if(el.dataset.key==='limit')value=Math.max(1,Math.min(100,value));
          if(el.dataset.key==='station_id'){
            const row=rows.find(r=>r.id===value);if(row)this._config={...this._config,fuel:row.kind==='ev'?'kwh':'all'};
          }
          this._change(el.dataset.key,value);
        });
        const filter=this.shadowRoot.querySelector('[data-filter]');if(filter)filter.oninput=()=>{const pos=filter.selectionStart;this._filter=filter.value;this._render();const next=this.shadowRoot.querySelector('[data-filter]');next.focus();next.setSelectionRange(pos,pos);};
        this.shadowRoot.querySelectorAll('[data-favorite]').forEach(el=>el.onchange=()=>{const set=new Set(this._config.favorites||[]);el.checked?set.add(el.dataset.favorite):set.delete(el.dataset.favorite);this._change('favorites',[...set]);this._render();});
        this.shadowRoot.querySelectorAll('[data-brand]').forEach(el=>el.onchange=()=>{const set=new Set(this._config.brands||[]);el.checked?set.add(el.dataset.brand):set.delete(el.dataset.brand);this._change('brands',[...set]);this._render();});
      }
    }
    class PricesCard extends StationCard {}
    class SingleStationCard extends StationCard {static getStubConfig(){return {fuel:'all',limit:1};}}
    class FavoritesCard extends StationCard {static getStubConfig(){return {fuel:'all',favorites:[],limit:8,sort:'name'};}}
    customElements.define('tiny-refuel-stations-editor',StationEditor);
    for(const [type,Class,name,description] of [
      ['tiny-refuel-prices-card',PricesCard,'Tiny Refuel · Prisoversigt','Stationspriser med søgning, drivmiddel og afstand – uden køretøj'],
      ['tiny-refuel-station-card',SingleStationCard,'Tiny Refuel · Station','Din stations priser, navigation og lokale prishistorik'],
      ['tiny-refuel-favorites-card',FavoritesCard,'Tiny Refuel · Favoritter','Dine udvalgte stationer samlet i ét kort']]){
      customElements.define(type,Class);window.customCards=window.customCards||[];
      window.customCards.push({type,name,description,preview:true});
    }
    // Pure contracts used by the offline frontend test suite.
    PricesCard.selectRows=selectRows;
    PricesCard.dashboardTools=Object.freeze({StationCard,StationEditor,css:extraCSS,esc,fmt,stamp,valid,coords,origin,distance,snapshot,selectRows,fuels});
  }
  if(customElements.get('tiny-refuel-card'))register();
  else customElements.whenDefined('tiny-refuel-card').then(register);
})(window);
