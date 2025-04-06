#/usr/bin/python
# Script para buscas de subdomínios utilizando o crt.sh
# A saída do script é limpa, ele somente mostra as urls que estão ativas!

import os
import sys
import random
import aiohttp
import asyncio
import json
import datetime
import aiofiles
from fake_useragent import UserAgent
from pathlib import Path

activate = sys.argv
USER_AGENT = UserAgent(platforms="mobile",min_version=120.0,safe_attrs=('__injections__',)).random

HEADERS = {
    "User-Agent": (
        "{}".format(USER_AGENT)
    )
}

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
   print("python3 sub.py <domínio> sem http:// | https:// ou www")
   raise SystemExit

async def extrair_subdominios(dominio: str) -> list:
    url = f"https://crt.sh/?q=%25.{dominio}&output=json"
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    print("\033[1;31m[!] Erro ao acessar crt.sh...\033[m")
                    return []
                texto = await resp.text()
                try:
                    dados = json.loads(texto)
                except json.JSONDecodeError:
                    print("\033[1;31m[!] Erro ao decodificar resposta do crt.sh, tente novamente...\033[m")
                    return []
                subdominios = set()
                for entrada in dados:
                    nome = entrada.get("name_value")
                    if nome:
                        for linha in nome.splitlines():
                            if dominio in linha:
                                subdominios.add(linha.strip())

                return list(subdominios)
    except Exception as e:
        print("\033[1;31m[!] Não foi possível realizar o scraping, verifique o domínio ou espere um pouco e tente novamente!\033[m")
        raise SystemExit
    except KeyboardInterrupt:
        raise SystemExit

async def verificar_subdominio(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        async with session.get(f"http://{url}", timeout=5, allow_redirects=True) as response:
            if response.status == 200:
                return url
    except KeyboardInterrupt:
        raise SystemExit
    except:
        pass
    try:
        async with session.get(f"https://{url}", timeout=5, ssl=False, allow_redirects=True) as response:
            if response.status == 200:
                return url
    except: 
        pass
    return None


async def verificar_todos(subdominios: list) -> list:
    ativos = []
    timeout = aiohttp.ClientTimeout(total=10)
    connector = aiohttp.TCPConnector(limit=50)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=HEADERS) as session:
        tarefas = [verificar_subdominio(session, sub) for sub in subdominios]
        for resultado in asyncio.as_completed(tarefas):
            ativo = await resultado
            if ativo:
                try:
                  if ativo.startswith("*"):
                    pass
                  else:
                    print("[{}] \033[1;32m[*] Subdomínio ativo\033[m: \033[1m{}\033[m".format(datetime.datetime.now().strftime("%H:%M:%S"),ativo))
                    ativos.append(ativo)
                except KeyboardInterrupt:
                  raise SystemExit
    return ativos


async def main():
    dominio = sys.argv[1].strip()
    print("""\033[1;3{}m
         _   ___ _       _         
 ___ _ _| |_|  _|_|___ _| |___ ___ 
|_ -| | | . |  _| |   | . | -_|  _|
|___|___|___|_| |_|_|_|___|___|_|\033[m
            \033[1;36mInstagram: @nanoxsec
\033[m""".format(random.randint(1,6)).strip())
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
    print("\n[{}] \033[1;32m[+] Coletando subdomínios de:\033[m [ {} ]".format(datetime.datetime.now().strftime("%H:%M:%S"),sys.argv[1]))
    subdominios = await extrair_subdominios(dominio)
    print("[{}] \033[1;32m[+]\033[m Total de subdomínios encontrados: [ {} ] \n".format(datetime.datetime.now().strftime("%H:%M:%S"),len(subdominios)))

    print("[{}] \033[1;33m[*] Filtrando subdomínios ativos...\033[m\n".format(datetime.datetime.now().strftime("%H:%M:%S")))
    ativos = await verificar_todos(subdominios)

    if len(ativos) >= 1:
      print("\n[{}] \033[1m[*]\033[m Foi adicionado \033[1;4m{}\033[m urls de subdomínios ativos no arquivo: [ {} ]\n".format(datetime.datetime.now().strftime("%H:%M:%S"),len(ativos),sys.argv[1]+".txt"))
      async with aiofiles.open(os.path.join("Resultados",sys.argv[1]+".txt"),"a") as add:
        for sub in ativos:
          await add.write(sub+"\n")

if __name__ == "__main__":
    if len(activate) != 2:
      helper()
    if "-h" in sys.argv[1] or "--help" in sys.argv[1]:
      helper()
    create_path()
    clear_screen()
    try:
      asyncio.run(main())
    except KeyboardInterrupt:
      raise SystemExit
