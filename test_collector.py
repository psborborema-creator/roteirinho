import unittest
from collector import JsonLd, objects, parse_event, region, sesc_sessions
class Tests(unittest.TestCase):
 def test_jsonld(self):
  p=JsonLd();p.feed('<script type="application/ld+json">{"@graph":[{"@type":"Event","name":"Oficina"}]}</script>')
  self.assertEqual(len(list(objects(__import__("json").loads(p.blocks[0])))),1)
 def test_region(self):
  self.assertEqual(region("Sesc São Gonçalo"),"São Gonçalo")
 def test_event(self):
  e={"@type":"Event","name":"Oficina Infantil","startDate":"2099-11-07T15:00:00-03:00","location":{"name":"CCBB Rio Centro","address":{"addressLocality":"Rio de Janeiro"}}}
  self.assertEqual(parse_event(e,{"url":"https://example.org"},"2026-10-29")["regiao"],"Centro")
 def test_sesc_html(self):
  src={"url":"https://www.sescrio.org.br/programacao/educacao/exemplo/"}
  page="<h1>Sesc São Gonçalo: Exposição Interativa Ciência Divertida</h1><p>gratuito</p><p>Sesc São Gonçalo</p><p>31/10 - 09h às 17h</p>"
  rows=sesc_sessions(page,src,"2026-10-30")
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]["data"],"2026-10-31")
  self.assertEqual(rows[0]["hora"],"09:00")
  self.assertEqual(rows[0]["preco_min"],0)
  self.assertEqual(rows[0]["regiao"],"São Gonçalo")
 def test_sesc_repeat_same_id(self):
  src={"url":"https://www.sescrio.org.br/programacao/educacao/exemplo/"}
  page="<h1>Sesc São Gonçalo: Ciência Divertida</h1><p>Sesc São Gonçalo</p><p>31/10 - 09h às 17h</p>"
  a=sesc_sessions(page,src,"2026-10-30")
  b=sesc_sessions(page,src,"2026-10-30")
  self.assertEqual(a[0]["id"],b[0]["id"])
 def test_no_outside(self):
  e={"name":"X","startDate":"2099-11-07","location":{"name":"São Paulo"}}
  self.assertIsNone(parse_event(e,{"url":"https://example.org"},"2026-10-29"))
if __name__=="__main__":unittest.main()
