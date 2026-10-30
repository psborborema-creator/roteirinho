"""Primeiro ciclo: descobrir candidatos em 3 fontes, sem publicar automaticamente."""
import datetime as dt
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
from collector import fetch, JsonLd, objects, parse_event

ROOT = Path(__file__).resolve().parent
TARGETS = [
    ("Sesc RJ", "https://www.sescrio.org.br/programacao/"),
    ("Rio com Crianças", "https://riocomcriancas.com.br/"),
    ("Pequenos no Rio", "https://pequenosnorio.com.br/"),
]
MAX_LINKS_PER_SOURCE = 12
class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            url = dict(attrs).get("href", "")
            if url:
                self.links.append(url)

def relevant(url, host):
    p = urlparse(url)
    if p.scheme not in ("http", "https") or p.hostname != host:
        return False
    if any(x in p.path.lower() for x in ("/wp-", "/feed", "/tag/", "/author/", "/categoria/", "/category/")):
        return False
    return True

def discover():
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date().isoformat()
    candidates, reports, seen = [], [], set()
    for name, homepage in TARGETS:
        report = {"fonte": name, "paginas_lidas": 0, "candidatos": 0, "erros": []}
        try:
            page = fetch(homepage)
            report["paginas_lidas"] += 1
            links = Links()
            links.feed(page)
            host = urlparse(homepage).hostname
            urls = [homepage]
            for raw in links.links:
                url = urldefrag(urljoin(homepage, raw)).url
                if relevant(url, host) and url not in urls:
                    urls.append(url)
                if len(urls) >= MAX_LINKS_PER_SOURCE + 1:
                    break
            for url in urls:
                try:
                    html = page if url == homepage else fetch(url)
                    if url != homepage:
                        report["paginas_lidas"] += 1
                    parser = JsonLd()
                    parser.feed(html)
                    for block in parser.blocks:
                        try:
                            parsed = json.loads(block)
                        except (ValueError, TypeError):
                            continue
                        for obj in objects(parsed):
                            event = parse_event(obj, {"url": url}, today)
                            if not event:
                                continue
                            key = (event["nome"].casefold(), event["data"], event.get("hora"), event["local"].casefold())
                            if key in seen:
                                continue
                            seen.add(key)
                            event["status_confirmacao"] = "candidato_nao_validado"
                            event["fonte_descoberta"] = name
                            event["pagina_descoberta"] = url
                            candidates.append(event)
                            report["candidatos"] += 1
                except Exception as exc:
                    report["erros"].append({"url": url, "erro": str(exc)[:120]})
        except Exception as exc:
            report["erros"].append({"url": homepage, "erro": str(exc)[:120]})
        reports.append(report)
    output = {"gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(), "publicacao_automatica": False, "metodo": "JSON-LD Event em ate 13 paginas por fonte; nao cobre materias sem dados estruturados", "relatorio": reports, "candidatos": candidates}
    (ROOT / "candidatos.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fontes": len(reports), "candidatos": len(candidates), "relatorio": reports}, ensure_ascii=False))
if __name__ == "__main__":
    discover()
