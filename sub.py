#/usr/bin/python
# Script para buscas de subdomínios utilizando o crt.sh
# A saída do script é limpa, ele somente mostra as urls que estão ativas!

import os
import sys
import asyncio
import aiohttp
import aiofiles
import datetime
from bs4 import BeautifulSoup
from pathlib import Path
from fake_useragent import UserAgent

activate = sys.argv
USER_AGENT = UserAgent(platforms="mobile",min_version=120.0,safe_attrs=('__injections__',)).random
HEADERS = {"User-Agent": "{}".format(USER_AGENT)}
PORTS = [80, 443, 8080, 8443, 8000, 3000]

def create_path():
   PATH_ATUAL = Path.cwd()
   os.makedirs(str(PATH_ATUAL)+"/Resultados",exist_ok=True)

def clear_screen():
  try:
    os.system("clear")
  except:
    os.system("cls")
  finally:
    pass

def helper():
   clear_screen()
   print("[+] Como utilizar:\n")
   print("-h ou --help --> Mostra essa mensagem de ajuda")
   print("python3 sub.py <domínio> sem http:// | https:// ou www\n")
   raise SystemExit

async def fetch_crtsh(domain):
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return list(set(entry["name_value"] for entry in data))
    except:
        return []

async def fetch_certspotter(domain):
    url = f"https://api.certspotter.com/v1/issuances?domain={domain}&include_subdomains=true&expand=dns_names"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return list({d for entry in data for d in entry["dns_names"]})
    except:
        return []

async def fetch_rapiddns(domain):
    url = f"https://rapiddns.io/subdomain/{domain}?full=1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, timeout=10) as resp:
                html = await resp.text()
                return list(set(re.findall(rf"([\w\.-]+\.{domain})", html)))
    except:
        return []

async def fetch_dnsdumpster(domain):
    url = "https://dnsdumpster.com/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS) as init:
                cookies = init.cookies
                html = await init.text()
                token = re.search(r'name="csrfmiddlewaretoken" value="(.+?)"', html)
                if not token:
                    return []

                payload = {"csrfmiddlewaretoken": token.group(1), "targetip": domain}
                async with session.post(url, data=payload, headers={"Referer": url, **HEADERS}, cookies=cookies) as resp:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    table = soup.find("table")
                    if not table:
                        return []
                    return list(set(re.findall(rf"([\w\.-]+\.{domain})", table.text)))
    except:
        return []

async def check_alive(subdomains):
    active = []

    conn = aiohttp.TCPConnector(limit=500, ssl=False)
    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        async def check(sub):
            for port in PORTS:
                scheme = "https" if port in [443, 8443] else "http"
                url = f"{scheme}://{sub}:{port}"
                try:
                    async with session.get(url, headers=HEADERS, allow_redirects=True) as resp:
                        if resp.status == 200:
                            if not sub.startswith("*"):
                              print("[{}] \033[1;32m[*] Subdomínio ativo\033[m: \033[1m{}\033[m".format(datetime.datetime.now().strftime("%H:%M:%S"),sub))
                              active.append(url)
                              return
                except:
                    continue

        await asyncio.gather(*(check(sub) for sub in subdomains))

    return active

async def enumerate_subdomains(domain):
    print("""\033[1;31m
         _   ___ _       _         
 ___ _ _| |_|  _|_|___ _| |___ ___ 
|_ -| | | . |  _| |   | . | -_|  _|
|___|___|___|_| |_|_|_|___|___|_|\033[m
             \033[1;36mInstagram:\033[m\033[1m @nanoxsec\033[m
""".strip())
    print("\n")
    remove_this = []
    remover_from_url = ["https://","http://","www","/"]
    for remove in remover_from_url:
      if remove in sys.argv[1]:
         remove_this.append(remove)
    if len(remove_this) >= 1:
      print("[{}] \033[1;31m[!]\033[m Remova da url do domínio:".format(datetime.datetime.now().strftime("%H:%M:%S")))
      for x in remove_this:
        print("---> {}".format(x))
      raise SystemExit
    print("[{}] \033[1;32m[+] Coletando subdomínios de:\033[m [ {} ]".format(datetime.datetime.now().strftime("%H:%M:%S"),sys.argv[1]))

    tasks = await asyncio.gather(
        fetch_crtsh(domain),
        fetch_certspotter(domain),
        fetch_rapiddns(domain),
        fetch_dnsdumpster(domain),
        return_exceptions=True
    )

    all_subs = set()
    for result in tasks:
        if isinstance(result, list):
            all_subs.update(result)

    print("[{}] \033[1;32m[+]\033[m Total de subdomínios encontrados: [ {} ]\n".format(datetime.datetime.now().strftime("%H:%M:%S"),len(all_subs)))
    print("[{}] \033[1;33m[*] Filtrando subdomínios ativos...\033[m\n".format(datetime.datetime.now().strftime("%H:%M:%S")))

    ativos = await check_alive(all_subs)
    if len(ativos) >= 1:
      async with aiofiles.open(os.path.join("Resultados",sys.argv[1]+".txt"),"a") as add:
        for subd in ativos:
          await add.write(subd+"\n")
      print("\n[{}] \033[1;32m[+]\033[m Foi adicionado \033[1;4m{}\033[m urls de subdomínios ativos no arquivo: [ {}.txt ]".format(datetime.datetime.now().strftime("%H:%M:%S"),len(ativos),sys.argv[1]))

if __name__ == "__main__":
    if "-h" in sys.argv[1] or "--help" in sys.argv[1]:
      helper()
    if len(activate) != 2:
      helper()
    create_path()
    clear_screen()
    try:
        asyncio.run(enumerate_subdomains(sys.argv[1]))
    except KeyboardInterrupt:
        print("\n[!] Execução interrompida pelo usuário.")
