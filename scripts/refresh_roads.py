"""Small local road overlay for when external map tiles are unreachable."""
import json,pathlib,urllib.request,urllib.parse
API='https://services.arcgis.com/0L95CJ0VTaxqcmED/ArcGIS/rest/services/TRANSPORTATION_street_segment/FeatureServer/0/query'
features=[];offset=0
while True:
 query=urllib.parse.urlencode(dict(f='geojson',where='1=1',geometry='-97.790,30.227,-97.704,30.370',geometryType='esriGeometryEnvelope',inSR=4326,outSR=4326,spatialRel='esriSpatialRelIntersects',outFields='FULL_STREET_NAME,ROAD_CLASS',returnGeometry='true',geometryPrecision=5,maxAllowableOffset=.00003,orderByFields='OBJECTID',resultOffset=offset,resultRecordCount=2000))
 with urllib.request.urlopen(API+'?'+query,timeout=60) as r:data=json.load(r)
 if 'error' in data:raise RuntimeError(data['error'])
 batch=data.get('features',[]);features+=batch
 if len(batch)<2000:break
 offset+=len(batch)
root=pathlib.Path(__file__).resolve().parents[1]
target=root/'data/roads.json';temp=target.with_suffix('.tmp');temp.write_text(json.dumps(dict(type='FeatureCollection',source=API,features=features),ensure_ascii=False,separators=(',',':')),encoding='utf-8');temp.replace(target)
print('Saved',len(features),'road segments')
