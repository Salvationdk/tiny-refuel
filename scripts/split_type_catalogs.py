"""Build clean type catalogs without guessing types or removing pending capacities."""
import argparse
import copy
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

FILES={'personbil':'car.json','varebil':'van.json','lastbil':'truck.json','motorcykel':'motorcycle.json','knallert':'moped.json','bus':'bus.json','traktor':'tractor.json','andet':'other.json'}
FIELDS={'fuel_types','model','brændstof','tank_l','batteri_kwh','requires_fuel_selection','vehicle_types','source_names','model_years','capacity_status','capacity_source_urls','capacity_checked_at','battery_basis','capacity_scope','capacity_documentation'}
VARIANT_FIELDS={'name','fuel_types','tank_l','batteri_kwh','battery_basis','model_years','capacity_status','capacity_scope','capacity_source_urls','capacity_checked_at','capacity_documentation'}

def key(text):return ' '.join(unicodedata.normalize('NFKC',text).casefold().split())

def build(data, output, version):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    groups={t:{} for t in FILES};quarantine=[]
    for brand in data['brands']:
        make=' '.join(brand['mærke'].split())
        for original in brand['modeller']:
            label=' '.join(original['model'].split())
            # Definite registry placeholders are quarantined, never silently discarded.
            if not make or not label or make.isdigit() or make in ('-','?'):
                quarantine.append({'make':make,'model':label,'reason':'unresolved_register_identity'});continue
            model={f:copy.deepcopy(v) for f,v in original.items() if f in FIELDS}
            model['model']=label
            for f in ('tank_l','batteri_kwh'):
                v=model.get(f)
                model[f]=v if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>0 else None
            if original.get('variants'):
                variants=[{f:copy.deepcopy(v) for f,v in row.items() if f in VARIANT_FIELDS} for row in original['variants'] if row.get('name') and any(row.get(f) is not None for f in ('tank_l','batteri_kwh'))]
                if variants:model['variants']=variants
            if model.get('model_years'):
                model['model_years']=sorted({str(y) for y in model['model_years'] if str(y).isdigit() and 1886<=int(y)<=2027})
            # Keep useful capacity/configuration notes, drop repeated import boilerplate.
            note=original.get('specification_note','')
            if note and note not in ('DMR-import mangler tjek',):model['specification_note']=note
            types=[('varebil' if t=='varevogn' else t) for t in original.get('vehicle_types',[])]
            types=sorted(set(t for t in types if t in FILES))
            if not types:types=['andet']
            model['vehicle_types']=types
            for t in types:
                mk=key(make);bucket=groups[t].setdefault(mk,{'mærke':make,'modeller':{}})
                modelkey=key(label)
                if modelkey in bucket['modeller']:
                    quarantine.append({'make':make,'model':label,'reason':'duplicate_normalized_identity'});continue
                bucket['modeller'][modelkey]=model
    index={'schema_version':1,'version':version,'catalogs':{}}
    for t,filename in FILES.items():
        brands=[{'mærke':b['mærke'],'modeller':[b['modeller'][k] for k in sorted(b['modeller'])]} for _,b in sorted(groups[t].items())]
        catalog={'schema_version':1,'version':version,'vehicle_type':t,'note':'Kapaciteter med needs_review er bevaret arbejdsdata og mangler kildekontrol.','brands':brands}
        raw=(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode()
        (output/filename).write_bytes(raw)
        index['catalogs'][t]={'file':filename,'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw),'models':sum(len(b['modeller']) for b in brands)}
    (output/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
    return index,quarantine

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--version',required=True);p.add_argument('--report',required=True);a=p.parse_args()
    index,quarantine=build(json.loads(Path(a.input).read_text(encoding='utf-8-sig')),a.output,a.version)
    Path(a.report).write_text(json.dumps({'catalogs':index['catalogs'],'quarantine':quarantine},ensure_ascii=False,indent=2)+'\n')
