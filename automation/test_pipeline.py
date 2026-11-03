import unittest,copy
from pipeline import merge,key,uid

def record(hour='15:00',local='Teatro dos Quatro – Shopping da Gávea'):
 return dict(nome='Peça infantil',data='2026-11-07',hora=hour,local=local,periodo='',fonte='teste')
class QueueTests(unittest.TestCase):
 def test_repeated_runs_keep_one(self):
  q={'candidatos':[]};q,a=merge(q,[record(),record()],'one','2026-11-03');q,b=merge(q,[record()],'two','2026-11-03');self.assertEqual(len(q['candidatos']),1);self.assertEqual(b['novos'],0);self.assertEqual(a['duplicatas_na_coleta'],1)
 def test_preserve_missing_and_editorial(self):
  q,_=merge({'candidatos':[]},[record()],'one','2026-11-03');q['candidatos'][0]['status_editorial']='rejeitado';q,s=merge(q,[],'two','2026-11-03');self.assertEqual(q['candidatos'][0]['status_editorial'],'rejeitado');self.assertEqual(s['preservados'],1)
 def test_expired_not_deleted(self):
  q,_=merge({'candidatos':[]},[record()],'one','2026-11-08');self.assertTrue(q['candidatos'][0]['expirado']);self.assertEqual(len(q['candidatos']),1)
 def test_different_times_venues(self):
  q,_=merge({'candidatos':[]},[record(),record('17:00'),record(local='Teatros da Barra')],'one','2026-11-03');self.assertEqual(len(q['candidatos']),3)
 def test_original_data_immutable(self):
  q,_=merge({'candidatos':[]},[record()],'one','2026-11-03');r=record();r['preco']='10';q,_=merge(q,[r],'two','2026-11-03');self.assertNotIn('preco',q['candidatos'][0]['dados']);self.assertEqual(q['candidatos'][0]['observacao_atual']['preco'],'10')
if __name__=='__main__':unittest.main()
