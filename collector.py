"""Public-event ingestion. Only explicit public URLs; no social scraping or credentials."""
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "fontes.json"
OUTPUT = ROOT / "eventos.json"
UA = "Roteirinho/1.1 (+public cultural event discovery)"

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.in_title = False
        self.title = ""
    def handle_starttag(self, tag, attrs):
        if tag == "h1":
            self.in_title = True
        if tag in ("p", "div", "li", "h1", "h2", "br"):
            self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag == "h1":
            self.in_title = False
    def handle_data(self, data):
        s = data.strip()
        if s:
            self.parts.append(s)
            if self.in_title:
                self.title += s + " "

def sesc_sessions(page, source, today):
    """Read explicitly dated sessions from a Sesc RJ official event page."""
    if "www.sescrio.org.br/programacao/" not in source["url"]:
        return []
    p = VisibleText()
    p.feed(page)
    title = re.sub(r"^Sesc [^:]+:\s*", "", p.title.strip())
    if not title:
        return []
    raw = " ".join(p.parts)
    location_match = re.search(r"Sesc (?:São Gonçalo|Duque de Caxias|Nova Iguaçu|Niterói|Tijuca|Madureira)", raw, re.I)
    location = location_match.group(0) if location_match else ""
    reg = region(location)
    if not reg:
        return []
    year = int(today[:4])
    results = []
    for match in re.finditer(r"(?<!\d)(\d{2})/(\d{2})\s*[-–]\s*(\d{1,2})h(?:\d{2})?", raw):
        day, month, hour = map(int, match.groups())
        try:
            date = dt.date(year, month, day).isoformat()
        except ValueError:
            continue
        if date < today or hour > 23:
            continue
        name = title
        identity = f"{name.casefold()}|{date}|{hour:02d}:00|{location.casefold()}"
        results.append({
            "id": "auto-" + hashlib.sha256(identity.encode()).hexdigest()[:20],
            "nome": name, "data": date, "hora": f"{hour:02d}:00",
            "local": location, "bairro": location, "regiao": reg,
            "categoria": "Exposição" if "exposição" in raw.lower() else "Evento",
            "descricao": "", "preco_min": 0 if re.search(r"\bgratuito\b", raw, re.I) else None,
            "preco_texto": "Gratuito" if re.search(r"\bgratuito\b", raw, re.I) else "Preço a confirmar",
            "idade_min": None, "idade_max": None, "url": source["url"],
            "fonte_tipo": "Sesc RJ — página oficial",
            "verificado_em": dt.datetime.now(dt.timezone.utc).isoformat()
        })
    return results

class JsonLd(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.buf = []
        self.blocks = []
    def handle_starttag(self, tag, attrs):
        if tag == "script" and "ld+json" in dict(attrs).get("type", "").lower():
            self.active = True
            self.buf = []
    def handle_data(self, data):
        if self.active:
            self.buf.append(data)
    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            self.blocks.append("".join(self.buf))
            self.active = False

def objects(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from objects(item)
    elif isinstance(obj, dict):
        typ = obj.get("@type", [])
        if isinstance(typ, str):
            typ = [typ]
        if any(str(t).endswith("Event") for t in typ):
            yield obj
        for value in obj.values():
            if isinstance(value, (list, dict)):
                yield from objects(value)

def region(location):
    value = location.lower()
    for label, words in {
        "Grande Tijuca": ["tijuca", "grajaú", "grajau", "vila isabel", "maracanã", "maracana", "andaraí", "andarai"],
        "Centro": ["centro", "lapa", "santa teresa", "gamboa", "saúde", "saude"],
        "Zona Sul": ["copacabana", "botafogo", "ipanema", "leblon", "gávea", "gavea", "flamengo", "jardim botânico", "são conrado"],
        "Zona Oeste": ["campo grande", "bangu", "realengo", "santa cruz"],
        "Zona Sudoeste": ["barra da tijuca", "recreio", "jacarepaguá", "jacarepagua"],
        "Niterói": ["niterói", "niteroi"],
        "São Gonçalo": ["são gonçalo", "sao goncalo"],
        "Duque de Caxias": ["duque de caxias"],
        "Nova Iguaçu": ["nova iguaçu", "nova iguacu"],
        "Queimados": ["queimados"],
        "Nilópolis": ["nilópolis", "nilopolis"],
    }.items():
        if any(w in value for w in words):
            return label
    return None

def text(value):
    return re.sub(r"<[^>]+>", " ", html.unescape(str(value or ""))).strip()

def parse_event(e, source, today):
    name = text(e.get("name"))
    start = str(e.get("startDate") or "")
    if not name or not re.match(r"^\d{4}-\d{2}-\d{2}", start) or start[:10] < today:
        return None
    location = e.get("location") or {}
    if isinstance(location, list):
        location = location[0] if location else {}
    if not isinstance(location, dict):
        location = {}
    address = location.get("address") or {}
    if isinstance(address, dict):
        address = " ".join(text(address.get(k)) for k in ("streetAddress", "addressLocality", "addressRegion"))
    place = text(location.get("name"))
    reg = region(place + " " + str(address))
    if not reg:
        return None  # Avoid importing out-of-scope events.
    offers = e.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}
    price = offers.get("lowPrice", offers.get("price"))
    try:
        price = float(price) if price is not None else None
    except (ValueError, TypeError):
        price = None
    url = str(e.get("url") or source["url"])
    if urlparse(url).scheme not in ("https", "http"):
        url = source["url"]
    identity = "|".join([name.casefold(), start[:16], place.casefold()])
    return {
        "id": "auto-" + hashlib.sha256(identity.encode()).hexdigest()[:20],
        "nome": name, "data": start[:10],
        "hora": start[11:16] if re.match(r"^\d\d:\d\d", start[11:]) else None,
        "local": place or "Local a confirmar", "bairro": text(address),
        "regiao": reg, "categoria": "Evento",
        "descricao": text(e.get("description"))[:500],
        "preco_min": price,
        "preco_texto": ("Gratuito" if price == 0 else "Preço a confirmar" if price is None else f"A partir de R$ {price:.2f}"),
        "idade_min": None, "idade_max": None, "url": url,
        "fonte_tipo": "Dados estruturados de página pública",
        "verificado_em": dt.datetime.now(dt.timezone.utc).isoformat()
    }

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read(2_000_000).decode("utf-8", "replace")

def run():
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date().isoformat()
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["fontes"]
    old = json.loads(OUTPUT.read_text(encoding="utf-8"))
    existing = [e for e in old.get("eventos", []) if e.get("data", "") >= today]
    seen = {(e.get("nome", "").casefold(), e.get("data"), e.get("hora"), e.get("local", "").casefold()) for e in existing}
    added = 0
    errors = []
    scanned = 0
    source_report = []
    for source in sources:
        if not source.get("ativo", True):
            continue
        try:
            page = fetch(source["url"])
            parser = JsonLd()
            parser.feed(page)
            scanned += 1
            before = added
            candidates = sesc_sessions(page, source, today)
            for event in candidates:
                key = (event["nome"].casefold(), event["data"], event.get("hora"), event["local"].casefold())
                if key not in seen:
                    existing.append(event)
                    seen.add(key)
                    added += 1
            for block in parser.blocks:
                try:
                    data = json.loads(block)
                except ValueError:
                    continue
                for obj in objects(data):
                    event = parse_event(obj, source, today)
                    if not event:
                        continue
                    key = (event["nome"].casefold(), event["data"], event.get("hora"), event["local"].casefold())
                    if key not in seen:
                        existing.append(event)
                        seen.add(key)
                        added += 1
            source_report.append({"fonte": source["nome"], "url": source["url"], "status": "sem_eventos_estruturados" if added == before else "eventos_importados", "blocos_jsonld": len(parser.blocks), "sessoes_html": len(candidates), "novos": added - before})
        except Exception as exc:
            errors.append({"fonte": source["url"], "erro": str(exc)[:160]})
            source_report.append({"fonte": source["nome"], "url": source["url"], "status": "erro", "novos": 0})
    if sources and scanned == 0:
        raise SystemExit("Falha total: nenhuma fonte consultada; base anterior preservada.")
    existing.sort(key=lambda e: (e["data"], e.get("hora") or "", e.get("nome") or ""))
    old.update({
        "atualizado_em": dt.datetime.now(dt.timezone.utc).isoformat(),
        "eventos": existing, "novos_encontrados": added,
        "fontes_consultadas": scanned, "relatorio_fontes": source_report, "erros_coleta": errors,
        "modo": "Base mista: registros de agendas públicas e eventos extraídos de JSON-LD. Confirmar detalhes na fonte."
    })
    OUTPUT.write_text(json.dumps(old, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fontes_consultadas": scanned, "novos": added, "total": len(existing), "erros": errors}, ensure_ascii=False))

if __name__ == "__main__":
    run()
