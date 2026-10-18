import argparse, json, re, unicodedata, copy, zipfile
from pathlib import Path
if __package__:
    from .vehicle_catalog import load_catalog
else:
    from vehicle_catalog import load_catalog
ROOT=Path(__file__).resolve().parent

def key(s):
    s=unicodedata.normalize('NFC',s).casefold().strip()
    return re.sub(r'\s+',' ',re.sub(r'\s*/\s*','/',s))
ALIASES={'chervolet':'CHEVROLET','dodg':'Dodge','dee tomaso':'DE TOMASO','detomaso':'DE TOMASO','saangyong':'SSANGYONG','artic cat':'ARCTIC CAT'}
# Explicit spelling aliases only; ambiguous initials are not inferred.
ALIASES.update({
    'a. j. s.': 'AJS', 'cf moto': 'CFMOTO', 'citroen': 'Citroën',
    'cityel': 'CITY-EL', 'e max': 'E-MAX', 'emax': 'E-MAX',
    'ez-go': 'E-Z-GO', 'her chee': 'HERCHEE', 'hurlimann': 'HÜRLIMANN',
    'i.h.': 'IH', 'j c b': 'JCB', 'jon way': 'JONWAY',
    'kassbohrer': 'KÄSSBOHRER', 'mercedes–benz/warmiaki': 'Mercedes-Benz/Warmiaki',
    'multi car': 'MULTICAR', 'multi track': 'MULTITRACK',
    'rolls royce': 'ROLLS-ROYCE', 'taylor dunn': 'TAYLOR-DUNN',
    'zhong-neng': 'ZHONGNENG',
})
EXCLUDED_MAKES={'selvbyg'}
INVALID={'-','ukendt','uoplyst','unknown','testkørsel','uspec.mærke',''}
def invalid(s): return key(s) in INVALID or s.strip().isdigit()
def merge(dst,src,context,conflicts):
    for k,v in src.items():
        if k not in dst or dst[k] is None: dst[k]=copy.deepcopy(v)
        elif dst[k]==v or v is None: continue
        elif isinstance(dst[k],list) and isinstance(v,list):
            for item in v:
                if item not in dst[k]: dst[k].append(copy.deepcopy(item))
        else:
            conflicts.append({'context':context,'field':k,'retained':dst[k],'alternative':v})
            dst.setdefault('cleanup_alternatives',{}).setdefault(k,[])
            if v not in dst['cleanup_alternatives'][k]: dst['cleanup_alternatives'][k].append(copy.deepcopy(v))

def clean_model_labels(data):
    """Strip a repeated make only when the shorter model already exists."""
    prepared = copy.deepcopy(data)
    renames = []
    for brand in prepared['brands']:
        names = {key(m['model']): m['model'] for m in brand['modeller']}
        preferred, renamed = [], []
        prefix = brand['mærke'] + ' '
        for model in brand['modeller']:
            name = model['model']
            suffix = name[len(prefix):].strip() if name.casefold().startswith(prefix.casefold()) else ''
            if suffix and key(suffix) in names:
                model.setdefault('source_names', [])
                if name not in model['source_names']: model['source_names'].append(name)
                model['model'] = names[key(suffix)]
                renames.append({'make': brand['mærke'], 'from': name, 'to': model['model']})
                renamed.append(model)
            else:
                preferred.append(model)
        brand['modeller'] = preferred + renamed
    result, report, excluded = clean(prepared)
    report['model_renames'] = renames
    result['model_label_cleanup'] = {k: v for k, v in report.items() if k not in ('coverage_rows', 'conflicts')}
    return result, report, excluded


def clean(data):
    result=copy.deepcopy(data); brands={}; quarantine=[]; changes=[]; conflicts=[]
    # Prefer names already present as an exact catalog label before creating an alias label.
    existing_names={key(b['mærke']):b['mærke'] for b in data['brands']}
    for original in sorted(data['brands'], key=lambda b: key(b['mærke']) in ALIASES):
        raw=original['mærke']
        if key(raw) in EXCLUDED_MAKES:
            quarantine.append({'reason':'self_build_excluded_by_user','entry':copy.deepcopy(original)}); continue
        canonical=ALIASES.get(key(raw),raw)
        name=existing_names.get(key(canonical),canonical)
        name=re.sub(r'\s*/\s*','/',re.sub(r'\s+',' ',unicodedata.normalize('NFC',name)).strip())
        if invalid(name):
            quarantine.append({'reason':'placeholder_or_numeric_make','entry':copy.deepcopy(original)}); continue
        bk=key(name)
        if bk not in brands:
            brands[bk]={k:copy.deepcopy(v) for k,v in original.items() if k not in ('mærke','modeller')}
            brands[bk].update({'mærke':name,'modeller':[]})
        target=brands[bk]
        if raw!=target['mærke']:
            changes.append({'from':raw,'to':target['mærke']})
            target.setdefault('source_names',[])
            if raw not in target['source_names']: target['source_names'].append(raw)
        merge(target,{k:v for k,v in original.items() if k not in ('mærke','modeller')},name,conflicts)
        models={key(m['model']):m for m in target['modeller']}
        for model in original['modeller']:
            mk=key(model['model'])
            if mk in INVALID or not any(c.isalnum() for c in model['model']):
                quarantine.append({'reason':'placeholder_model','make':raw,'entry':copy.deepcopy(model)}); continue
            if mk not in models:
                models[mk]=copy.deepcopy(model); target['modeller'].append(models[mk])
            else:
                entry=models[mk]
                if model.get('requires_fuel_selection') or entry.get('requires_fuel_selection'):
                    preserved = {field: entry.get(field) if entry.get(field) is not None else model.get(field) for field in ('brændstof', 'tank_l', 'batteri_kwh') if entry.get(field) is not None or model.get(field) is not None}
                    if preserved: entry['preserved_specification'] = preserved
                if model['model']!=entry['model']:
                    entry.setdefault('source_names',[])
                    if model['model'] not in entry['source_names']:entry['source_names'].append(model['model'])
                merge(entry,{k:v for k,v in model.items() if k!='model'},name+'/'+entry['model'],conflicts)
        for model in target['modeller']:
            variants={}
            for v in model.get('variants',[]):
                vk=key(v['name'])
                if vk not in variants:variants[vk]=copy.deepcopy(v)
                else:
                    if v['name']!=variants[vk]['name']:
                        variants[vk].setdefault('source_names',[])
                        if v['name'] not in variants[vk]['source_names']:variants[vk]['source_names'].append(v['name'])
                    merge(variants[vk],{k:value for k,value in v.items() if k!='name'},name+'/'+model['model']+'/'+v['name'],conflicts)
            if 'variants' in model:model['variants']=sorted(variants.values(),key=lambda v:key(v['name']))
        target['modeller'].sort(key=lambda m:key(m['model']))
    result['brands']=sorted(brands.values(),key=lambda b:key(b['mærke']))
    report={'original_makes':len(data['brands']),'cleaned_makes':len(result['brands']),
        'original_models':sum(len(b['modeller']) for b in data['brands']),
        'cleaned_models':sum(len(b['modeller']) for b in result['brands']),
        'original_variants':sum(len(m.get('variants',[])) for b in data['brands'] for m in b['modeller']),
        'cleaned_variants':sum(len(m.get('variants',[])) for b in result['brands'] for m in b['modeller']),
        'renames':changes,'quarantined_entries':len(quarantine),'conflicts':conflicts,
        'conflict_count':len(conflicts),'requires_review':bool(conflicts),
        'note':'Conservative cleanup. Coachbuilders, historic makes and uncertain names retained. Original import counts remain in dmr_catalog; current counts are here. No new capacity data inferred.'}
    # Match each retained register label to existing assets without renaming the asset.
    norm=lambda x: ''.join(c for c in unicodedata.normalize('NFKD',x).casefold() if c.isalnum())
    assets={norm(n):(n,f) for field,f in [('logos','svg'),('logo_pngs','png'),('logo_urls','external')]
            for n in result.get(field,{})}
    aliases=result.setdefault('logo_aliases',{})
    for alias,target in list(aliases.items()):
        if norm(target) in assets: assets[norm(alias)]=assets[norm(target)]
    coverage=[]
    for brand in result['brands']:
        name=brand['mærke'];found=assets.get(norm(name))
        if found:
            coverage.append({'make':name,'status':'available','asset_key':found[0],'format':found[1]})
            if name!=found[0]: aliases[name]=found[0]
        else:
            coverage.append({'make':name,'status':'pending',
                'reason':'combined_name_requires_separate_review' if '/' in name else 'no_verified_asset'})
    available=sum(x['status']=='available' for x in coverage)
    combined=sum(x['status']=='pending' and '/' in x['make'] for x in coverage)
    result['logo_coverage']={'scope':'All make labels in this cleaned full motor-vehicle catalog',
        'register_makes':len(coverage),'covered':available,'pending':len(coverage)-available,
        'pending_combined':combined,'pending_single_names':len(coverage)-available-combined,
        'svg_assets':len(result.get('logos',{})),'png_assets':len(result.get('logo_pngs',{})),
        'external_assets':len(result.get('logo_urls',{}))}
    report['logo_coverage']=result['logo_coverage']
    report['coverage_rows']=coverage
    result['catalog_cleanup']={k:v for k,v in report.items() if k!='coverage_rows'}
    return result,report,quarantine


def main():
    parser=argparse.ArgumentParser(description='Conservative cleanup; preserve original and quarantine excluded labels.')
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    destinations=[args.output_dir/name for name in ('bilkatalog.json','oprydningsrapport.json','udskilte-poster.json')]
    if args.input.resolve() in {p.resolve() for p in destinations}:
        parser.error('Output must not overwrite the input catalog')
    data=load_catalog(args.input)
    result,report,quarantine=clean(data)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for path,payload in zip(destinations,(result,report,quarantine)):
        path.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('coverage_rows','renames','conflicts','note')},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
