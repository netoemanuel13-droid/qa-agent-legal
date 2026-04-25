"""
export_workflows.py
Exporta todos os workflows do n8n e salva como JSON em backup/
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


def slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("—", "_")
        .replace("-", "_")
        .replace("→", "")
        .strip("_")
    )


def fetch_all_workflows() -> list:
    url = f"{N8N_URL}/api/v1/workflows"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def fetch_workflow_detail(workflow_id: str) -> dict:
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def save_backup(name: str, workflow_id: str, detail: dict) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{slugify(name)}__{workflow_id}.json"
    path = BACKUP_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=2)
    return path


def main():
    if not API_KEY:
        print("ERRO: variável N8N_API_KEY não definida.")
        print("  export N8N_API_KEY='sua_key_aqui'")
        sys.exit(1)

    print(f"Conectando em {N8N_URL} ...")
    workflows = fetch_all_workflows()
    print(f"Encontrados {len(workflows)} workflows.\n")

    summary = []
    for wf in workflows:
        wf_id = wf["id"]
        wf_name = wf["name"]
        print(f"  Exportando [{wf_id}] {wf_name} ...")
        detail = fetch_workflow_detail(wf_id)
        path = save_backup(wf_name, wf_id, detail)
        node_count = len(detail.get("nodes", []))
        summary.append({"id": wf_id, "name": wf_name, "nodes": node_count, "file": str(path)})
        print(f"    -> {node_count} nós salvos em {path.name}")

    # Salvar índice
    index_path = BACKUP_DIR / "_index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Backup completo! {len(workflows)} workflows salvos em backup/")
    print(f"   Índice: {index_path}")
    return summary


if __name__ == "__main__":
    main()
