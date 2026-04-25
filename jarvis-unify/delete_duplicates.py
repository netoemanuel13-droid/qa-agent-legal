"""
delete_duplicates.py
ATENÇÃO: Execute SOMENTE após confirmar que o JARVIS MASTER está funcionando.
Deleta todos os workflows secundários (mantém apenas o JARVIS MASTER).
"""

import requests
import json
import os
import sys
from pathlib import Path

N8N_URL = os.getenv("N8N_BASE_URL", "https://n8n-68n4.srv1583766.hstgr.cloud")
API_KEY = os.getenv("N8N_API_KEY", "")

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json",
}

BACKUP_DIR = Path(__file__).parent / "backup"


def load_index() -> list:
    index_path = BACKUP_DIR / "_index.json"
    with open(index_path, encoding="utf-8") as f:
        return json.load(f)


def delete_workflow(workflow_id: str) -> bool:
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}"
    resp = requests.delete(url, headers=HEADERS, timeout=30)
    return resp.status_code in (200, 204)


def main():
    if not API_KEY:
        print("ERRO: N8N_API_KEY não definida.")
        sys.exit(1)

    index = load_index()

    to_delete = [e for e in index if "JARVIS MASTER" not in e["name"].upper()]
    master = [e for e in index if "JARVIS MASTER" in e["name"].upper()]

    print("=" * 60)
    print("⚠️  ATENÇÃO: Esta operação é IRREVERSÍVEL.")
    print(f"   Serão deletados {len(to_delete)} workflows.")
    print(f"   Será mantido:   {master[0]['name'] if master else 'N/A'}")
    print()
    print("Workflows que serão DELETADOS:")
    for e in to_delete:
        print(f"  [{e['id']}] {e['name']}")
    print("=" * 60)

    confirm = input("\nDigite 'DELETAR' para confirmar: ").strip()
    if confirm != "DELETAR":
        print("Operação cancelada.")
        sys.exit(0)

    deleted = []
    failed = []

    for entry in to_delete:
        print(f"  Deletando [{entry['id']}] {entry['name']} ...")
        ok = delete_workflow(entry["id"])
        if ok:
            deleted.append(entry)
            print(f"    ✅ Deletado")
        else:
            failed.append(entry)
            print(f"    ❌ Falha ao deletar")

    print(f"\n✅ Deletados: {len(deleted)}")
    if failed:
        print(f"❌ Falhas:    {len(failed)}")
        for e in failed:
            print(f"  [{e['id']}] {e['name']}")


if __name__ == "__main__":
    main()
