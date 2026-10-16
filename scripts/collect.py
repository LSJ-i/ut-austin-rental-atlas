"""Collect public listings conservatively. Python standard library only.

No login, browser challenge bypass or detail-page scraping. Source failures retain
their previous observations; missing records are retired only after a full parse.
"""
import concurrent.futures,datetime as dt,hashlib,json,pathlib,re,time,urllib.error,urllib.parse,urllib.request
from html.parser import HTMLParser

ROOT=pathlib.Path(__file__).resolve().parents[1]
UA='UTRentalAtlas/2.0 (+https://github.com/LSJ-i/ut-austin-rental-atlas)'
class Node:
 def __init__(self,tag='',attrs=(),parent=None):self.tag=tag;self.attrs=dict(attrs);self.parent=parent;self.children=[]
 def text(self):return ' '.join(' '.join(c.text() if isinstance(c,Node) else c for c in self.children).split())
 def all(self,tag=None,cls=None):
  out=[]
  for c in self.children:
   if isinstance(c,Node):
    if (tag is None or c.tag==tag) and (cls is None or cls in c.attrs.get('class','').split()):out.append(c)
    out.extend(c.all(tag,cls))
  return out
 def one(self,tag=None,cls=None):return next(iter(self.all(tag,cls)),Node())
class DOM(HTMLParser):
 def __init__(self,html):super().__init__(convert_charrefs=True);self.root=Node();self.current=self.root;self.feed(html)
 def handle_starttag(self,tag,attrs):
  n=Node(tag,attrs,self.current);self.current.children.append(n)
  if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.current=n
 def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)
 def handle_endtag(self,tag):
  n=self.current
  while n.parent:
   if n.tag==tag:self.current=n.parent;return
   n=n.parent
 def handle_data(self,data):self.current.children.append(data)
def amounts(text):return [float(v.replace(',','')) for v in re.findall(r'\$([\d,]+(?:\.\d+)?)',text)]
def date_value(text,today):
 text=text.strip()
 if re.search(r'\bnow\b',text,re.I):return today
 for fmt in ('%m/%d/%y','%m/%d/%Y','%B %d, %Y'):
  try:return dt.datetime.strptime(text,fmt).date().isoformat()
  except ValueError:pass
 return None
def in_scope(coords,zones):
 lat,lng=coords
 return any(w<=lng<e and s<=lat<n for w,s,e,n in [z['bounds'] for z in zones])
def base_row(id,name,address,beds,baths,rent,coords,source,**kw):
 row=dict(id=id,name=name,address=address,beds=beds,baths=baths,rent=rent,coordinates=coords,source=source,sqft=None,status='advertised',availableFrom=None,furnished='unknown',smart=False,googleRating=None,ratingSource=None,priceBasis='monthly',term=None,notes='',recordType='floorplan')
 row.update(kw);return row
def parse_bridge(html,today):
 dom=DOM(html).root;rows=[]
 for box in dom.all(cls='floorplan-details-container'):
  name=box.one(cls='floorplan-name').text();stats=[s.text() for s in box.all(cls='stat-value')];prices=amounts(box.one(cls='floorplan-rent').text());av=box.one(cls='floorplan-availability').text()
  if not name or len(stats)!=3 or not prices:raise ValueError('Bridge floorplan structure changed')
  beds=0 if 'studio' in stats[0].lower() else int(re.search(r'\d+',stats[0])[0]);baths=float(re.search(r'[\d.]+',stats[1])[0]);sqft=int(re.search(r'[\d,]+',stats[2])[0].replace(',',''));d=date_value(av.replace('Available on ',''),today)
  status='future' if d and d>today else 'limited' if 'Vacant' in av else 'available' if av=='Available' else 'needs-confirmation'
  href=box.one('a',cls='floorplan-link').attrs.get('href','/floorplans')
  rows.append(base_row('bridge-'+name.lower(),'Bridge at Northwest Hills · '+name,'3600 Greystone Dr',beds,baths,min(prices),[30.358889,-97.7515933],urllib.parse.urljoin('https://www.bridgeatnorthwesthills.com',href),sqft=sqft,status=status,availableFrom=d,rentMax=max(prices),availabilityText=av,propertyName='Bridge at Northwest Hills',notes='官网户型报价范围；具体房号、租期及强制费用需联系物业确认。'))
 if len(rows)<4:raise ValueError('Bridge incomplete floorplan list')
 return rows
def parse_appfolio(html,today,source,zones):
 match=re.search(r'\bmarkers:\s*(\[.*?\]),\s*\n',html,re.S)
 if not match:raise ValueError('AppFolio map data missing')
 markers={str(x['listing_id']):x for x in json.loads(match[1])};dom=DOM(html).root;boxes=dom.all(cls='js-listing-item');rows=[]
 if not boxes:raise ValueError('Empty AppFolio list; retain previous snapshot')
 for box in boxes:
  key=box.attrs.get('id','').replace('listing_','');m=markers.get(key)
  if not m:raise ValueError('AppFolio listing lacks map metadata')
  coords=[m.get('latitude'),m.get('longitude')]
  if None in coords or not in_scope(coords,zones):continue
  spec=m.get('unit_specs','');m_bed=re.search(r'([\d.]+)\s*bd',spec);m_bath=re.search(r'([\d.]+)\s*ba',spec)
  if not m_bed and re.search('studio',spec,re.I):m_bed=re.match(r'(0)','0')
  if not m_bath or not m_bed:raise ValueError('Unrecognized AppFolio bed/bath: '+spec)
  prices=amounts(m['rent_range'])
  if not prices:raise ValueError('AppFolio rent missing')
  facts={b.one('dt').text().lower():b.one('dd').text() for b in box.all(cls='detail-box__item')}
  av=facts.get('available','');d=date_value(av,today)
  title=box.one(cls='js-listing-title').text();sqft=facts.get('square feet','').replace(',','')
  rows.append(base_row(source['id']+'-'+key,title,m['address'],int(float(m_bed[1])),float(m_bath[1]),min(prices),coords,urllib.parse.urljoin(source['url'],m['detail_page_url']),sqft=int(sqft) if sqft.isdigit() else None,status='future' if d and d>today else 'available' if d else 'needs-confirmation',availableFrom=d,availabilityText=av,recordType='unit',propertyName=m['address'].split(',')[0].split(' - ')[0].split('#')[0].strip(),notes='管理公司公开招租页。'+('页面写明 NOW；可以申请，不代表可以保留至计划日期。' if av.upper()=='NOW' else '公布日期与实际交付仍需确认。')))
 return rows
def parse_acc_detail(data,today,seed):
 if not data.get('Layouts'):raise ValueError('ACC layouts missing')
 rows=[]
 for layout in data['Layouts']:
  title=layout['Title'];p=layout.get('AdjustedPrice');m=re.search(r'(\d+)\s*Bed\s*-\s*([\d.]+)\s*Bath',title,re.I)
  if not m or not isinstance(p,(float,int)) or p<=0:raise ValueError('Unrecognized ACC layout')
  av=layout.get('Availability',{}).get('AvText','');status='waitlist' if 'wait' in av.lower() or 'sold' in av.lower() else 'limited' if 'limited' in av.lower() else 'available' if av.lower()=='available' else 'needs-confirmation'
  row=base_row('block-'+layout['ID'],'The Block · '+title,seed['address'],int(m[1]),float(m[2]),p,seed['coordinates'],'https://www.americancampus.com/student-apartments/tx/austin/the-block/floor-plans#/detail/'+layout['UrlSlug'],smart='SMART' in title,furnished='no' if 'Unfurnished' in title else 'yes' if 'Furnished' in title else 'unknown',priceBasis='installment',status=status,term=data.get('TermName'),originalRent=layout.get('Price'),provider='acc',providerId=layout['ID'],apiPath=seed['apiPath'],propertyName='The Block · '+title.split(':')[0],notes='ACC 官方接口报价；按人按期付款，非整套月租。SMART 资格、优惠与起租日需物业确认。',availabilityText=av)
  rows.append(row)
 return rows
def robot_allowed(text,url):
 # Longest matching Allow/Disallow wins; supports * and terminal $.
 groups=[];agents=[];rules=[]
 for raw in text.splitlines():
  line=raw.split('#',1)[0].strip()
  if ':' not in line:continue
  key,value=[s.strip() for s in line.split(':',1)];key=key.lower()
  if key=='user-agent':
   if rules:groups.append((agents,rules));agents=[];rules=[]
   agents.append(value.lower())
  elif key in ('allow','disallow') and value:rules.append((key,value))
 groups.append((agents,rules));path=urllib.parse.urlsplit(url).path;matches=[]
 for agents,rules in groups:
  if '*' not in agents and not any('utrentalatlas'.startswith(a) for a in agents):continue
  for kind,pattern in rules:
   expr='^'+re.escape(pattern).replace(r'\*','.*').replace(r'\$','$')
   if re.search(expr,path):matches.append((len(pattern.replace('*','').replace('$','')),kind=='allow'))
 return max(matches,default=(0,True))[1]
class Client:
 def __init__(self):self.robots={};self.last={}
 def get(self,url):
  host=urllib.parse.urlsplit(url).netloc
  if host not in self.robots:
   robot='https://'+host+'/robots.txt'
   try:text=self.raw(robot)
   except urllib.error.HTTPError as e:
    if e.code==404:text=''
    else:raise
   self.robots[host]=text
  if not robot_allowed(self.robots[host],url):raise RuntimeError('robots.txt does not allow this path')
  delay=re.search(r'(?im)^crawl-delay:\s*(\d+)',self.robots[host]);interval=max(1,float(delay[1]) if delay else 1)
  time.sleep(max(0,interval-(time.monotonic()-self.last.get(host,0))))
  return self.raw(url)
 def raw(self,url):
  req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/json'})
  try:
   for attempt in range(3):
    try:
     with urllib.request.urlopen(req,timeout=35) as r:
      content=r.read(8_000_001)
      if len(content)>8_000_000:raise RuntimeError('Response exceeds safety limit')
      return content.decode('utf-8')
    except urllib.error.HTTPError:raise
    except urllib.error.URLError:
     if attempt==2:raise
     time.sleep(2**attempt)
  finally:self.last[urllib.parse.urlsplit(url).netloc]=time.monotonic()
def merge_source(previous,new,source,now,changes):
 old={x['id']:x for x in previous if x.get('sourceId')==source['id']};out=[]
 if old and len(new)<len([x for x in old.values() if x['status']!='unavailable'])*.3:raise ValueError('Unexpected inventory drop >70%; retain previous snapshot')
 for row in new:
  before=old.get(row['id'],{});row={**before,**row}
  if row.get('availabilityText','').upper()=='NOW' and before.get('availabilityText','').upper()=='NOW':row['availableFrom']=before.get('availableFrom',row['availableFrom'])
  row.update(sourceId=source['id'],sourceType=source['type'],updateMode='automatic',observedAt=now,checkedAt=now[:10],firstSeenAt=before.get('firstSeenAt',now),lastSeenAt=now)
  row['propertyId']=hashlib.sha256(re.sub(r'[^a-z0-9]','',row.get('propertyName',row['address']).lower()).encode()).hexdigest()[:12]
  row['provenance']={k:{'url':row['source'],'observedAt':now} for k in ['rent','status','availableFrom']}
  diffs={k:{'before':before.get(k),'after':row.get(k)} for k in ['rent','status','availableFrom'] if before and before.get(k)!=row.get(k)}
  if diffs:changes.append({'id':row['id'],'name':row['name'],'at':now,'fields':diffs})
  row['changedAt']=now if diffs else before.get('changedAt',now);out.append(row)
 seen={x['id'] for x in new}
 for id,row in old.items():
  if id not in seen:
   row=dict(row,status='unavailable',retiredAt=now,retiredReason='Not included in current collection scope or response; not proof of lease status');out.append(row)
 return out
def atomic(path,data):
 temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
def main():
 now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds');today=now[:10];inventory=json.loads((ROOT/'data/listings.json').read_text(encoding='utf-8-sig'));sources=json.loads((ROOT/'data/sources.json').read_text(encoding='utf-8-sig'));zones=json.loads((ROOT/'data/areas.json').read_text(encoding='utf-8-sig'))['zones'];changes=json.loads((ROOT/'data/changes.json').read_text(encoding='utf-8-sig')) if (ROOT/'data/changes.json').exists() else []
 def collect(source):
  client=Client()
  if source['adapter']=='bridge':return parse_bridge(client.get(source['url']),today)
  if source['adapter']=='appfolio':return parse_appfolio(client.get(source['url']),today,source,zones)
  if source['adapter']=='acc':
   rows=[];paths={x['apiPath']:x for x in inventory['listings'] if x.get('provider')=='acc'}
   if not paths:raise ValueError('No tracked ACC floorplans')
   for path,seed in paths.items():rows+=parse_acc_detail(json.loads(client.get('https://www.americancampus.com'+path)),today,seed)
   return rows
  raise ValueError('Unknown adapter')
 active=[s for s in sources['sources'] if s.get('adapter')]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures={s['id']:pool.submit(collect,s) for s in active}
  for s in active:
   s['lastAttemptAt']=now
   try:
    rows=futures[s['id']].result();merged=merge_source(inventory['listings'],rows,s,now,changes);inventory['listings']=[x for x in inventory['listings'] if x.get('sourceId')!=s['id']]+merged
    s.update(status='ok',lastSuccessAt=now,count=len(rows),error=None);print(s['id'],'OK',len(rows))
   except Exception as e:s.update(status='error',error=str(e)[:180]);print(s['id'],'FAILED',str(e)[:180])
 inventory.update(lastAttemptAt=now,lastSuccessfulCollectionAt=max((s.get('lastSuccessAt') or '' for s in active),default=''),scope='多个公开来源的定时采集与人工核查；非实时库存，也不是全部市场。')
 inventory['updatedAt']=max(x['checkedAt'] for x in inventory['listings']);sources['updatedAt']=now
 # Keep only a bounded, deduplicated change history.
 unique={json.dumps(c,sort_keys=True):c for c in changes};changes=sorted(unique.values(),key=lambda c:c['at'])[-300:]
 atomic(ROOT/'data/listings.json',inventory);atomic(ROOT/'data/sources.json',sources);atomic(ROOT/'data/changes.json',changes)
 if not any(s.get('status')=='ok' and s.get('lastSuccessAt')==now for s in active):raise SystemExit('Every automatic source failed; prior observations retained')
if __name__=='__main__':main()

