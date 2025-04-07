import os
import sys
import asyncio
import aiohttp
import aiofiles
import datetime
import re
from bs4 import BeautifulSoup
from pathlib import Path
from fake_useragent import UserAgent

USER_AGENT = UserAgent(platforms="mobile", min_version=120.0, safe_attrs=('__injections__',)).random
HEADERS = {"User-Agent": USER_AGENT}
PORTS = [80, 443]

def create_path():
    os.makedirs("Resultados", exist_ok=True)

def clear_screen():
    os.system("clear" if os.name == "posix" else "cls")

def helper():
    clear_screen()
    print("[+] Como utilizar:\n")
    print("-h ou --help --> Mostra essa mensagem de ajuda")
    print("python3 sub.py <domínio> sem http:// | https:// ou www\n")
    raise SystemExit

async def fetch_all_subdomains(domain):
    async def fetch(url, process):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=HEADERS, timeout=10) as resp:
                    return await process(resp)
        except:
            return []

    async def parse_crtsh(resp):
        if resp.status == 200:
            data = await resp.json()
            return list(set(entry["name_value"] for entry in data))
        return []

    async def parse_certspotter(resp):
        if resp.status == 200:
            data = await resp.json()
            return list({d for entry in data for d in entry["dns_names"]})
        return []

    async def parse_rapiddns(resp):
        html = await resp.text()
        return list(set(re.findall(rf"([\w\.-]+\.{domain})", html)))

    async def parse_dnsdumpster(_):
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

    tasks = await asyncio.gather(
        fetch(f"https://crt.sh/?q=%25.{domain}&output=json", parse_crtsh),
        fetch(f"https://api.certspotter.com/v1/issuances?domain={domain}&include_subdomains=true&expand=dns_names", parse_certspotter),
        fetch(f"https://rapiddns.io/subdomain/{domain}?full=1", parse_rapiddns),
        parse_dnsdumpster(None),
        return_exceptions=True
    )

    all_subs = set()
    for result in tasks:
        if isinstance(result, list):
            all_subs.update(result)
    return list(all_subs)
async def check_alive(subdomains, domain):
    active = []
    conn = aiohttp.TCPConnector(limit=1000, ssl=False)
    timeout = aiohttp.ClientTimeout(total=5)

    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        sem = asyncio.Semaphore(500)

        async def check(sub):
            async with sem:
                for port in PORTS:
                    scheme = "https" if port == 443 else "http"
                    url = f"{scheme}://{sub}:{port}"
                    try:
                        async with session.get(url, headers=HEADERS) as resp:
                            if resp.status == 200:
                                if not sub.startswith("*"):
                                    now = datetime.datetime.now().strftime("%H:%M:%S")
                                    print(f"[{now}] \033[1;32m[*] Subdomínio ativo\033[m: \033[1m{sub}\033[m")
                                    active.append(url)
                                    return
                    except:
                        pass

        await asyncio.gather(*[check(sub) for sub in subdomains if sub.lower() != domain.lower()])
    return active

async def main(domain):
    clear_screen()
    print("""\033[1;31m
         _   ___ _       _         
 ___ _ _| |_|  _|_|___ _| |___ ___ 
|_ -| | | . |  _| |   | . | -_|  _|
|___|___|___|_| |_|_|_|___|___|_|\033[m
             \033[1;36mInstagram:\033[m\033[1m @nanoxsec\033[m
""")
    print()

    if any(p in domain for p in ["https://", "http://", "www", "/"]):
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \033[1;31m[!]\033[m Remova da url do domínio:")
        print("---> https://\n---> http://\n---> www\n---> /")
        raise SystemExit

    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \033[1;32m[+] Coletando subdomínios de:\033[m [ {domain} ]")
    subs = await fetch_all_subdomains(domain)

    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \033[1;32m[+]\033[m Total de subdomínios encontrados: [ {len(subs)} ]\n")
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] \033[1;33m[*] Filtrando subdomínios ativos...\033[m\n")

    ativos = await check_alive(subs, domain)

    if ativos:
      lines = [url + "\n" for url in ativos]
      async with aiofiles.open(f"Resultados/{domain}.txt", "w") as f:
        await f.writelines(lines)
    print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] \033[1;32m[+]\033[m Foi adicionado \033[1;4m{len(ativos)}\033[m urls de subdomínios ativos no arquivo: [ {domain}.txt ]")
if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ["-h", "--help"]:
        helper()
    create_path()
    try:
        asyncio.run(main(sys.argv[1]))
    except KeyboardInterrupt:
        print("\n[!] Execução interrompida pelo usuário.")
