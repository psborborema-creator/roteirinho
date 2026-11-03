import unittest,copy
from processar import times,dedup,identity

def row(name='Brinquedos em Ação',date='2026-11-20',hour='16:00',place='Teatro dos Quatro – Shopping da Gávea – Gávea',old='old-1'):
 return dict(nome=name,data=date,hora=hour,local=place,id_anterior=old,ids_anteriores=[old],fontes=['teste'])
class EditorialTests(unittest.TestCase):
 def test_ids_distintos_mesma_sessao(self):
  a=row();b=row(name='BRINQUEDOS EM ACAO!',place='Teatro dos Quatro - Shopping da Gavea',old='old-2');out,d=dedup([a,b]);self.assertEqual(len(out),1);self.assertEqual(out[0]['ids_anteriores'],['old-1','old-2'])
 def test_locais_e_horarios_distintos(self):
  out,_=dedup([row(),row(hour='17:00'),row(place='Teatros da Barra')]);self.assertEqual(len(out),3)
 def test_horario_por_dia(self):
  s='22 e 29 de novembro; 22/11 – 15h e 29/11 – 16h';self.assertEqual(times(s,'2026-11-22'),['15:00']);self.assertEqual(times(s,'2026-11-29'),['16:00'])
 def test_multiplas_sessoes_e_turnos(self):
  self.assertEqual(times('14 de novembro; 15h e 17h','2026-11-14'),['15:00','17:00']);self.assertEqual(times('07 de novembro | 1º Turno: 11h às 13h e 2º Turno: 13h30 às 15h30','2026-11-07'),['11:00','13:30'])
 def test_sem_inventar_hora(self):self.assertEqual(times('28 de novembro; Ingressos a R$ 44,90','2026-11-28'),[])
 def test_idempotencia(self):
  a,_=dedup([row(),row(old='old-2')]);b,_=dedup(copy.deepcopy(a));self.assertEqual(a,b)
if __name__=='__main__':unittest.main()
