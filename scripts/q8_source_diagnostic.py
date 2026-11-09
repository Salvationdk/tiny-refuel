"""Temporary source diagnostic for issue 23: safe public response inspection."""
import html
import re
import urllib.request
import urllib.error
import json

URLS = [
  "https://beta.q8.dk/Station/GetStationPrices?page=1&pageSize=2000",
  "https://www.q8.dk/priser",
  "https://www.q8.dk/erhverv/priser",
  "https://www.f24.dk/Station/GetStationPrices?page=1&pageSize=500",
]
def inspect(url):
    print("SOURCE:", url, flush=True)
    req=urllib.request.Request(url,headers={
      "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept":"application/json,text/html;q=0.9,*/*;q=0.7",
    })
    try:
      with urllib.request.urlopen(req,timeout=18) as response:
        body=response.read(3_000_000).decode("utf-8",errors="replace")
        print("STATUS",response.status,"LENGTH",len(body),"TYPE",response.headers.get("content-type"),flush=True)
        if "/erhverv/priser" in url:
          import sys
          from pathlib import Path
          sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "custom_components" / "tiny_refuel"))
          import scraper
          tariffs=scraper.parse_q8_el_tariffs(body)
          print("LIVE PARSED Q8 TARIFFS",[(r["kind"],r["kwh"]) for r in tariffs],flush=True)
          assert len(tariffs)==2 and tariffs[0]["kwh"]>0 and tariffs[1]["kwh"]>0

        try:
          obj=json.loads(body)
          print("JSON top keys",list(obj)[:12] if isinstance(obj,dict) else type(obj).__name__,flush=True)
          if isinstance(obj,dict):
            data=obj.get("data",obj)
            if isinstance(data,dict):
              print("JSON data keys",list(data)[:15],flush=True)
              for k,v in data.items():
                if isinstance(v,list):
                  print("array",k,"count",len(v),"first item",str(v[0])[:400] if v else None,flush=True)
        except (json.JSONDecodeError,TypeError):
          for term in ["Vores Ladepriser til elbil","Pris på lynlader","Pris på 22","Betalningsmiddel","Betalingsmetode","stationsPrices","GoEasy 95","kr/kWh","<table"]:
            pos=body.find(term)
            print("KEY",term,"pos",pos,flush=True)
            if pos>=0:
              txt=html.unescape(body[max(0,pos-220):pos+400])
              print("SNIPPET",re.sub(r"\\s+"," ",txt)[:580],flush=True)
    except urllib.error.HTTPError as err:
      print("HTTP",err.code,flush=True);err.close()
    except Exception as err:
      print("ERROR",type(err).__name__,str(err)[:160],flush=True)

for url in URLS:inspect(url)
