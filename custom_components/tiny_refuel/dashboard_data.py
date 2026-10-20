"""Small dashboard summaries, distinct from vehicle positions and full catalogs."""
from .entity_data import has_location, positive

VEHICLE_FIELDS = ('id','navn','mærke','model','variant','aargang','koeretoejstype',
                  'brændstof','tank_liters','batteri_kwh','location_entity',
                  'capacity_status','capacity_source_urls','capacity_checked_at','capacity_scope')


def general_tariffs(data, failed=False):
    rows=[]
    for row in data.get('ev',[]):
        if not isinstance(row,dict) or has_location(row) or not positive(row.get('kwh')):
            continue
        rows.append({k:row.get(k) for k in ('brand','name','kind','kwh','source','source_updated')}
                    | {'current':not bool(failed or row.get('stale'))})
    return rows


def dashboard_snapshot(manager, catalogs=None, map_status=None):
    # Labels are shared with diagnostic entities, not inferred from provider codes.
    from .sensor import SOURCE_NAMES
    data=manager.data
    sources=[]
    for kind in ('fuel_sources','ev_sources'):
        for key,status in data.get(kind,{}).items():
            if not isinstance(status,dict):continue
            sources.append({'id':kind+':'+key,'kind':kind,
                            'name':SOURCE_NAMES.get(kind,{}).get(key,key),
                            **{k:status[k] for k in ('status','last_success','records','priced','missing_coordinates','error','last_error') if k in status}})
    return {'vehicles':[{k:v[k] for k in VEHICLE_FIELDS if k in v} for v in manager.vehicles],
            'updated':data.get('updated'),'last_attempt':manager.last_attempt,
            'last_error':manager.last_error,'refreshing':manager.refreshing,'progress':manager.progress,
            'sources':sources,'errors':data.get('errors',[]),'benefit_errors':data.get('benefit_errors',[]),
            'catalogs':catalogs.snapshot() if catalogs else {},
            'history':{'days':manager.history.days,'error':manager.history_error},
            'map':map_status or {'enabled':False,'count':0}}
