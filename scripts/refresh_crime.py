"""Aggregate public APD data. Publishes area totals only, never incident locations."""
import argparse, concurrent.futures, datetime as dt, json, math, pathlib, time, urllib.parse, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = 'https://maps.austintexas.gov/arcgis/rest/services/CrimeViewer_new/APD_Reported_Crimes_new/FeatureServer'
ZONES = [
 ('west-north','West Campus 北部','25th–29th / Pearl · Rio Grande',[-97.752,30.289,-97.742,30.297]),
 ('west-south','West Campus 南部','MLK–25th / San Gabriel · Nueces',[-97.752,30.281,-97.742,30.289]),
 ('north-university','North University','校园以北 / Guadalupe · Speedway',[-97.742,30.297,-97.729,30.311]),
 ('hyde-park','Hyde Park','住宅街区 / 38th–45th 周边',[-97.740,30.311,-97.720,30.326]),
 ('hancock','Hancock','Red River / 32nd–38th 周边',[-97.729,30.297,-97.711,30.311]),
 ('downtown-north','Downtown 北部','MLK 以南 / Capitol 周边',[-97.752,30.267,-97.730,30.281]),
 ('east-campus','East Campus 周边','I-35 以东 / Manor Road 周边',[-97.730,30.281,-97.711,30.297]),
 ('clarksville','Clarksville / West Downtown','Lamar 以西 / 663 与 Pease Park 周边',[-97.772,30.272,-97.752,30.300]),
 ('far-west','Far West','661 服务片区 / Greystone · North Hills',[-97.766,30.344,-97.742,30.370]),
 ('riverside','Riverside','670 / 672 服务片区 / Elmont · Lakeshore',[-97.742,30.227,-97.704,30.253]),
 ('lake-austin','Lake Austin Blvd','663 服务片区 / Brackenridge · Gateway',[-97.790,30.275,-97.772,30.291]),
]
def request(url, params):
    req=urllib.request.Request(url+'?'+urllib.parse.urlencode(params),headers={'User-Agent':'UTRentalAtlas/1.0 public-data research'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=60) as response: data=json.load(response)
            break
        except urllib.error.URLError:
            if attempt==2: raise
            time.sleep(2**attempt)
    if 'error' in data: raise RuntimeError(data['error'])
    return data

def fetch_layer(layer, start, end):
    all_features=[]; offset=0
    while True:
        envelope=','.join(str(fn(z[3][i] for z in ZONES)) for i,fn in [(0,min),(1,min),(2,max),(3,max)])
        result=request(f'{API}/{layer}/query',{'f':'json','where':f"OCCURRENCE_DATE >= TIMESTAMP '{start} 00:00:00' AND OCCURRENCE_DATE < TIMESTAMP '{end} 00:00:00'",'geometry':envelope,'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','outFields':'RIN,OCCURRENCE_DATE','outSR':4326,'returnGeometry':'true','orderByFields':'OBJECTID','resultOffset':offset,'resultRecordCount':2000})
        features=result.get('features',[])
        all_features.extend((layer,f) for f in features)
        if not result.get('exceededTransferLimit'): break
        if not features: raise RuntimeError('Pagination stopped before completion')
        offset+=len(features)
    return all_features

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--as-of',default=dt.datetime.now(dt.timezone.utc).date().isoformat()); parser.add_argument('--if-stale',action='store_true'); args=parser.parse_args()
    if args.if_stale:
        try:
            if json.loads((ROOT/'data/areas.json').read_text(encoding='utf-8-sig')).get('asOf')==args.as_of:
                print('Area statistics already current'); return
        except (OSError,ValueError): pass
    end=dt.date.fromisoformat(args.as_of); start=end-dt.timedelta(days=90)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda layer:fetch_layer(layer,start.isoformat(),end.isoformat()),range(9)))
    features=[item for group in results for item in group]
    zones=[]
    for key,name,description,bounds in ZONES:
        west,south,east,north=bounds; cases=set(); violence=set()
        for layer,feature in features:
            geometry=feature.get('geometry') or {}; x=geometry.get('x'); y=geometry.get('y')
            if x is None or y is None or not(west<=x<east and south<=y<north): continue
            rin=feature['attributes']['RIN']; cases.add(rin)
            if layer in (0,1,2): violence.add(rin)
        area=(east-west)*111.32*math.cos(math.radians((north+south)/2))*(north-south)*111.32
        zones.append({'id':key,'name':name,'description':description,'bounds':bounds,'areaKm2':round(area,3),'incidents':len(cases),'violentIncidents':len(violence),'density':round(len(cases)/area,1),'level':'unknown'})
    # Never award a reassuring tier to an all-empty feed.
    if any(z['incidents'] for z in zones):
        values=sorted(z['density'] for z in zones)
        low=values[(len(values)-1)//3]; high=values[2*(len(values)-1)//3]
        for z in zones: z['level']='low' if z['density']<=low else 'medium' if z['density']<=high else 'high'
    else: raise RuntimeError('All areas empty; retain previous snapshot')
    data={'asOf':end.isoformat(),'periodStart':start.isoformat(),'periodEnd':(end-dt.timedelta(days=1)).isoformat(),'days':90,'source':API,'sourceLabel':'Austin Police Department · CrimeViewer','sourceLatestIncident':dt.datetime.fromtimestamp(max(f['attributes']['OCCURRENCE_DATE'] for _,f in features)/1000,dt.timezone.utc).isoformat() if features else None,'method':'自定义研究范围内，近 90 天 APD 主要罪类按 RIN 去重后的报案数 / 平方公里；按本页研究范围密度的三分位分组，边界处相同值归入同组。暴力类仅指 homicide、robbery、aggravated assault。','limitations':['研究范围为自定义矩形，非官方社区边界；范围之间可能重叠。','不含 UTPD 单独记录、Part II 类及未报案事件；不代表完整犯罪数量。','未按常住人口、游客或通勤人口调整，不是个人受害概率或官方安全评级。','仅有本页研究范围的相对比较，低密度不代表安全；无覆盖数据不评为低风险。'],'zones':zones}
    target=ROOT/'data'/'areas.json'; target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.tmp'); temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); temporary.replace(target)
    print(json.dumps({'period':[data['periodStart'],data['periodEnd']],'zones':[{k:z[k] for k in ('id','incidents','density','level')} for z in zones]},ensure_ascii=False))
if __name__=='__main__': main()

