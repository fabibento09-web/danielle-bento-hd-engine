# danielle-bento-hd-engine

Motor de cálculo do Desenho Humano usado na calculadora gratuita de [danibentoconstelacao.com.br/desenho-humano](https://danibentoconstelacao.com.br/desenho-humano/).

Este repositório publica o código-fonte do cálculo, como pedem as licenças das bibliotecas que ele usa. Ele é atualizado sempre que o motor muda no site.

## O que tem aqui

| Caminho | O que é |
|---|---|
| `api/hd_engine.py` | Função serverless (Python, Vercel). Recebe data, hora e local de nascimento e devolve o mapa: tipo, estratégia, autoridade, perfil, centros, canais, portas, cruz de encarnação, variáveis e a imagem do bodygraph. |
| `api/_lib/humandesign/` | Biblioteca de cálculo, copiada do projeto humandesign_api (ver "Origem"). |
| `requirements.txt` | Dependências Python. |

## Como rodar

```bash
pip install -r requirements.txt
python -c "
import sys; sys.path.insert(0, 'api')
import hd_engine
r = hd_engine.calculate({'year': 1990, 'month': 6, 'day': 15, 'hour': 14, 'minute': 30,
                         'latitude': -23.5505, 'longitude': -46.6333, 'timezone': 'America/Sao_Paulo'})
print(r['type'], r['authority'], r['profile'])
"
```

Na Vercel, a função responde em `POST /api/hd_engine` com o mesmo corpo em JSON. Sem `latitude` e `longitude`, ela aceita `city` (texto) e resolve as coordenadas pelo Nominatim (OpenStreetMap).

## Origem e modificações

- `api/_lib/humandesign/` vem de [dturkuler/humandesign_api](https://github.com/dturkuler/humandesign_api), versão 3.4.1 (commit `a2cf558`, 23/01/2026), pasta `src/humandesign`. Copyright de Dogan Turkuler. Nessa versão, o projeto era distribuído sob a GPL-3.0.
- Arquivos removidos, por não serem usados (eram o servidor FastAPI): `api.py`, `dependencies.py` e a pasta `routers/`.
- Arquivos modificados (cada um tem um aviso no topo):
  - `features/core.py`, em 26/04/2026: imports de IPython e tqdm passaram a ser opcionais, para rodar numa função serverless.
  - `services/chart_renderer.py`, em 26/04/2026 (cores da marca e corpo só com contorno) e em 02/09/2026 (nomes de centros comparados de forma normalizada, para o Plexo Solar definido ser pintado).
- Todos os outros arquivos da biblioteca estão iguais ao original.
- `api/hd_engine.py` foi escrito para o site.

## Licença

- O conjunto publicado aqui está sob a **GNU Affero General Public License v3.0 ou posterior** (`LICENSE`).
- A biblioteca em `api/_lib/humandesign/` mantém a licença com que foi recebida, a **GPL-3.0** (`api/_lib/humandesign/LICENSE`). A seção 13 da GPL-3.0 permite combiná-la com código AGPL-3.0.
- O cálculo das posições dos planetas usa o [pyswisseph](https://github.com/astrorigin/pyswisseph), interface Python da [Swiss Ephemeris](https://www.astro.com/swisseph/) (Astrodienst AG), sob a AGPL-3.0. Ele é instalado pelo `requirements.txt`, sem modificações.

## English summary

Human Design chart engine behind the free calculator at danibentoconstelacao.com.br. The library in `api/_lib/humandesign/` is humandesign_api v3.4.1 by Dogan Turkuler (GPL-3.0), with the FastAPI server removed and two files modified (notices at the top of each). Planetary positions come from pyswisseph / Swiss Ephemeris (AGPL-3.0). This repository is published under AGPL-3.0-or-later to provide the source of the network service.
