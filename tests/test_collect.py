import copy,importlib.util,pathlib,unittest,tempfile,json
spec=importlib.util.spec_from_file_location('collect',pathlib.Path(__file__).resolve().parents[1]/'scripts/collect.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class CollectorTests(unittest.TestCase):
 def test_robots_specific_allow(self):
  robots='User-agent: *\nAllow: /listings$\nDisallow: /'
  self.assertTrue(c.robot_allowed(robots,'https://example.com/listings'))
  self.assertFalse(c.robot_allowed(robots,'https://example.com/listings/detail/x'))
 def test_dates_and_ranges(self):
  self.assertEqual(c.date_value('8/1/28','2026-10-16'),'2028-08-01');self.assertEqual(c.date_value('NOW','2026-10-16'),'2026-10-16');self.assertIsNone(c.date_value('Ask us','2026-10-16'));self.assertEqual(c.amounts('$1,200–$1,400'),[1200,1400])
 def test_invalid_page_retains_previous_data(self):
  with self.assertRaises(ValueError):c.parse_appfolio('<p>Temporarily unavailable</p>','2026-10-16',{'id':'test'},[])
  with self.assertRaises(ValueError):c.parse_bridge('<p>Challenge page</p>','2026-10-16')
 def test_complete_missing_record_is_retired_not_deleted(self):
  old=[dict(id=str(i),sourceId='s',status='available',rent=1000,availableFrom=None) for i in range(4)]
  new=[dict(id=str(i),name='Test',address='Test',status='available',rent=1100,availableFrom=None,source='https://test.com') for i in range(3)];changes=[]
  result=c.merge_source(old,new,{'id':'s','type':'official'},'2026-10-16T00:00:00Z',changes)
  self.assertEqual(len(result),4);self.assertEqual(result[-1]['status'],'unavailable');self.assertEqual(len(changes),3)
 def test_abnormal_drop_rejects_source(self):
  old=[dict(id=str(i),sourceId='s',status='available') for i in range(10)]
  with self.assertRaises(ValueError):c.merge_source(old,[],{'id':'s','type':'official'},'2026-10-16T00:00:00Z',[])
 def test_now_observation_does_not_advance_original_availability(self):
  row=dict(id='a',sourceId='s',name='Test',address='Test',rent=1000,status='available',availabilityText='NOW',availableFrom='2026-10-15',source='https://test.com')
  result=c.merge_source([row],[dict(row,availableFrom='2026-10-16')],{'id':'s','type':'manager'},'2026-10-16T00:00:00Z',[])
  self.assertEqual(result[0]['availableFrom'],'2026-10-15')
 def test_repeat_run_reads_unicode_history(self):
  original=c.ROOT
  try:
   with tempfile.TemporaryDirectory(prefix='.test-',dir=pathlib.Path(__file__).resolve().parent) as folder:
    c.ROOT=pathlib.Path(folder);(c.ROOT/'data').mkdir()
    for name,data in [('listings',{'listings':[{'checkedAt':'2026-10-15'}]}),('sources',{'sources':[]}),('areas',{'zones':[]}),('changes',[{'at':'2026-10-15','name':'户型价格变动'}])]:c.atomic(c.ROOT/'data'/f'{name}.json',data)
    with self.assertRaises(SystemExit):c.main()
    self.assertEqual(json.loads((c.ROOT/'data/changes.json').read_text(encoding='utf-8'))[0]['name'],'户型价格变动')
  finally:c.ROOT=original
if __name__=='__main__':unittest.main()
