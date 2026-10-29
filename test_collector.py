import unittest
from collector import JsonLd, objects, parse_event, region
class Tests(unittest.TestCase):
 def test_jsonld(self):
  p=JsonLd();p.feed('<script type="application/ld+json">{"@graph":[{"@type":"Event","name":"Oficina"}]}</script>')
  self.assertEqual(len(list(objects(__import__("json").loads(p.blocks[0])))),1)
 def test_region(self):
  self.assertEqual(region("Sesc São Gonçalo"),"São Gonçalo")
 def test_event(self):
  e={"@type":"Event","name":"Oficina Infantil","startDate":"2099-11-07T15:00:00-03:00","location":{"name":"CCBB Rio Centro","address":{"addressLocality":"Rio de Janeiro"}}}
  self.assertEqual(parse_event(e,{"url":"https://example.org"},"2026-10-29")["regiao"],"Centro")
 def test_no_outside(self):
  e={"name":"X","startDate":"2099-11-07","location":{"name":"São Paulo"}}
  self.assertIsNone(parse_event(e,{"url":"https://example.org"},"2026-10-29"))
if __name__=="__main__":unittest.main()
