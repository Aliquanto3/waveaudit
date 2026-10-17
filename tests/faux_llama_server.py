"""Faux binaire llama-server pour les tests de `LlamaServer` (story 12). Stdlib seulement.

Lancé comme `python -m faux_llama_server --host ... --port ... -c ... -t ...` : `LlamaServer`
passe `-m <gguf>`, et le test donne `gguf = Path("faux_llama_server")` avec ce dossier dans
`PYTHONPATH`. Comportement choisi par `FAUX_LLAMA_SCENARIO` :
- `nominal` : sert `GET /health` (200) et `GET /v1/models` ;
- `jamais_pret` : `/health` répond 503 ;
- `meurt` : quitte aussitôt (code 3) ;
- `meurt_une_fois` : quitte au premier lancement (crée `FAUX_LLAMA_MARQUEUR`), puis nominal.
Écrit sa ligne de commande sur la sortie standard (le journal de `LlamaServer`).
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> None:
    lecteur = argparse.ArgumentParser()
    lecteur.add_argument("--host", required=True)
    lecteur.add_argument("--port", type=int, required=True)
    lecteur.add_argument("-c", type=int, required=True)
    lecteur.add_argument("-t", type=int, required=True)
    lecteur.add_argument("--parallel")
    lecteur.add_argument("--no-webui", action="store_true")
    lecteur.add_argument("--jinja", action="store_true")
    args = lecteur.parse_args()
    print("ARGS " + json.dumps(sys.argv[1:]), flush=True)

    scenario = os.environ.get("FAUX_LLAMA_SCENARIO", "nominal")
    if scenario == "meurt":
        sys.exit(3)
    if scenario == "meurt_une_fois":
        marqueur = Path(os.environ["FAUX_LLAMA_MARQUEUR"])
        if not marqueur.exists():
            marqueur.write_text("1", encoding="utf-8")
            sys.exit(3)

    class Gestionnaire(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (API de http.server)
            if self.path == "/health":
                code = 503 if scenario == "jamais_pret" else 200
                self._repondre(code, {"status": "ok" if code == 200 else "loading"})
            elif self.path == "/v1/models":
                self._repondre(200, {"object": "list", "data": [{"id": "faux"}]})
            else:
                self._repondre(404, {})

        def _repondre(self, code: int, corps: dict) -> None:
            donnees = json.dumps(corps).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(donnees)))
            self.end_headers()
            self.wfile.write(donnees)

        def log_message(self, *args: object) -> None:
            pass

    ThreadingHTTPServer((args.host, args.port), Gestionnaire).serve_forever()


if __name__ == "__main__":
    main()
