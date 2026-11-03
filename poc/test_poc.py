import unittest
from coleta_poc import extract
class Tests(unittest.TestCase):
 def test_expired_and_future_html(self):
  b=b'<meta charset="utf-8"><h3>Test</h3><p>Em cartaz dias 01, 07 de novembro no Teatro X. Hor\xc3\xa1rio: 16h Ingressos online antecipados: por R$ 30.</p>'
  rows,rejected=extract('Pequenos no Rio',b,'https://example.org','2026-11-03')
  self.assertEqual([r['data'] for r in rows],['2026-11-07']);self.assertEqual(len(rejected),1)
 def test_no_invented_daily_range(self):
  rows,_=extract('Pequenos no Rio','<h3>Test</h3><p>Em cartaz dias 01 a 29 de novembro no Teatro X. Horário: 16h</p>'.encode(),'https://example.org','2026-11-03')
  self.assertEqual(rows,[])
if __name__=='__main__':unittest.main()
