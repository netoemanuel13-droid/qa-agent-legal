"""
unify_workflows.py
Une todos os workflows exportados em um único JARVIS MASTER no n8n.

Fluxo:
  1. Lê os JSONs de backup/
  2. Identifica o JARVIS MASTER (workflow base)
  3. Extrai e reposiciona nós de cada workflow secundário
  4. Resolve conflitos de nomes de nós
  5. Faz PATCH no JARVIS MASTER via API
  6. Ativa o workflow
"""

import requests
import json
import os
import sys
import copy
from pathlib import Path

N8N_URL = os.getenv("N8N_BASE_URL", "https://n8n-68n4.srv1583766.hstgr.cloud")
API_KEY = os.getenv("N8N_API_KEY", "")

HEADERS = {
    "X-N8N-API-KEY": API_KEY,
    "Content-Type": "application/json",
}

BACKUP_DIR = Path(__file__).parent / "backup"

# Mapeamento de palavras-chave do nome do workflow → offset Y no canvas
# O JARVIS MASTER fica em y=0; cada grupo ocupa uma faixa de 400px
Y_OFFSETS = [
    ("JARVIS MASTER",           0),
    ("JARVIS ENTRY",          400),
    ("JARVIS TTS",            800),
    ("JARVIS CHAT",          1200),
    ("HEALTH MONITOR",       1600),
    ("TELEGRAM JARVIS",      2000),
    ("TELEGRAM OPENCLAW",    2400),
    ("E-BOOK",               2800),
    ("EBOOK",                2800),
    ("INSTAGRAM",            3200),
    ("OMNICHAT",             3600),
    ("META ADS",             4000),
]

X_BASE = 200  # x inicial para todos os grupos secundários


def load_index() -> list:
    index_path = BACKUP_DIR / "_index.json"
    if not index_path.exists():
        print("ERRO: backup/_index.json não encontrado. Rode export_workflows.py primeiro.")
        sys.exit(1)
    with open(index_path, encoding="utf-8") as f:
        return json.load(f)


def load_workflow_json(file_path: str) -> dict:
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def get_y_offset(workflow_name: str) -> int:
    upper = workflow_name.upper()
    for keyword, offset in Y_OFFSETS:
        if keyword in upper:
            return offset
    # Workflows sem mapeamento recebem offset incremental no final
    return None


def resolve_name_conflicts(existing_names: set, nodes: list, prefix: str) -> tuple[list, dict]:
    """
    Renomeia nós que conflitem com nomes já existentes.
    Retorna (nodes_renomeados, mapa_de_renomeação).
    """
    rename_map = {}  # old_name -> new_name
    for node in nodes:
        original = node["name"]
        if original in existing_names:
            new_name = f"{prefix} › {original}"
            # Garantir unicidade
            counter = 2
            candidate = new_name
            while candidate in existing_names:
                candidate = f"{new_name} ({counter})"
                counter += 1
            rename_map[original] = candidate
            node["name"] = candidate
            existing_names.add(candidate)
        else:
            existing_names.add(original)
    return nodes, rename_map


def apply_rename_to_connections(connections: dict, rename_map: dict) -> dict:
    """
    Atualiza as chaves e referências internas do dict de conexões
    de acordo com o rename_map.
    """
    if not rename_map:
        return connections

    updated = {}
    for node_name, outputs in connections.items():
        new_name = rename_map.get(node_name, node_name)
        new_outputs = {}
        for output_type, output_list in outputs.items():
            new_output_list = []
            for connection_group in output_list:
                new_group = []
                for conn in connection_group:
                    new_conn = dict(conn)
                    new_conn["node"] = rename_map.get(conn["node"], conn["node"])
                    new_group.append(new_conn)
                new_output_list.append(new_group)
            new_outputs[output_type] = new_output_list
        updated[new_name] = new_outputs
    return updated


def reposition_nodes(nodes: list, y_offset: int, x_base: int = X_BASE) -> list:
    """
    Reposiciona nós para uma faixa exclusiva no canvas.
    Mantém posições relativas entre si, ajustando Y e normalizando X.
    """
    if not nodes:
        return nodes

    # Calcular bounding box atual
    xs = [n["position"][0] for n in nodes]
    ys = [n["position"][1] for n in nodes]
    min_x, min_y = min(xs), min(ys)

    for node in nodes:
        node["position"][0] = node["position"][0] - min_x + x_base
        node["position"][1] = node["position"][1] - min_y + y_offset

    return nodes


def patch_workflow(workflow_id: str, payload: dict) -> dict:
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}"
    resp = requests.patch(url, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def activate_workflow(workflow_id: str) -> dict:
    url = f"{N8N_URL}/api/v1/workflows/{workflow_id}/activate"
    resp = requests.post(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def merge_settings(master_settings: dict, other_settings: dict) -> dict:
    """Mantém as configurações do MASTER; ignora conflitos de outros workflows."""
    merged = dict(other_settings)
    merged.update(master_settings)
    return merged


def main():
    if not API_KEY:
        print("ERRO: variável N8N_API_KEY não definida.")
        print("  export N8N_API_KEY='sua_key_aqui'")
        sys.exit(1)

    index = load_index()
    print(f"Carregando {len(index)} workflows do backup ...\n")

    # Separar MASTER dos demais
    master_entry = None
    secondary = []

    for entry in index:
        if "JARVIS MASTER" in entry["name"].upper():
            master_entry = entry
        else:
            secondary.append(entry)

    if not master_entry:
        print("ERRO: Workflow 'JARVIS MASTER' não encontrado no backup.")
        print("  Verifique se o nome contém 'JARVIS MASTER'.")
        sys.exit(1)

    print(f"✅ JARVIS MASTER identificado: ID={master_entry['id']}  ({master_entry['nodes']} nós)")
    master_detail = load_workflow_json(master_entry["file"])

    # Copiar profundamente para não modificar o backup original
    unified_nodes = copy.deepcopy(master_detail.get("nodes", []))
    unified_connections = copy.deepcopy(master_detail.get("connections", {}))

    # Conjunto de nomes já em uso (para detecção de conflitos)
    existing_names = {n["name"] for n in unified_nodes}

    # Workflows sem mapeamento Y recebem slots extras a partir de 4400
    next_extra_y = 4400

    skipped = []

    for entry in secondary:
        wf_name = entry["name"]
        wf_detail = load_workflow_json(entry["file"])

        nodes = copy.deepcopy(wf_detail.get("nodes", []))
        connections = copy.deepcopy(wf_detail.get("connections", {}))

        if not nodes:
            print(f"  ⏭  [{entry['id']}] {wf_name} — sem nós, pulando.")
            skipped.append(entry)
            continue

        # Determinar offset Y
        y_offset = get_y_offset(wf_name)
        if y_offset is None:
            y_offset = next_extra_y
            next_extra_y += 400
            print(f"  ⚠️  [{entry['id']}] {wf_name} — sem mapeamento Y, usando y={y_offset}")
        else:
            print(f"  Mesclando [{entry['id']}] {wf_name} → y={y_offset} ({len(nodes)} nós)")

        # Reposicionar nós no canvas
        nodes = reposition_nodes(nodes, y_offset)

        # Resolver conflitos de nomes
        prefix = wf_name[:30]
        nodes, rename_map = resolve_name_conflicts(existing_names, nodes, prefix)

        # Atualizar referências nas conexões
        connections = apply_rename_to_connections(connections, rename_map)

        # Adicionar ao conjunto unificado
        unified_nodes.extend(nodes)
        unified_connections.update(connections)

    print(f"\nTotal de nós unificados: {len(unified_nodes)}")
    print(f"Total de conexões: {len(unified_connections)}")

    # Construir payload do PATCH
    payload = {
        "nodes": unified_nodes,
        "connections": unified_connections,
    }

    # Preservar configurações e metadados do MASTER, se existirem
    for field in ("settings", "staticData", "tags"):
        if field in master_detail:
            payload[field] = master_detail[field]

    # Salvar payload localmente antes de enviar (segurança)
    payload_path = BACKUP_DIR / "_unified_payload.json"
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nPayload salvo em {payload_path} (backup de segurança)")

    # PATCH no JARVIS MASTER
    print(f"\nAtualizando JARVIS MASTER (ID={master_entry['id']}) ...")
    result = patch_workflow(master_entry["id"], payload)
    print(f"✅ Patch aplicado com sucesso!")

    # Ativar o workflow
    print("Ativando JARVIS MASTER ...")
    activate_workflow(master_entry["id"])
    print("✅ JARVIS MASTER ativado!\n")

    if skipped:
        print(f"⚠️  Workflows pulados (sem nós): {[e['name'] for e in skipped]}")

    print("=" * 60)
    print("JARVIS MASTER unificado com sucesso!")
    print(f"  ID do workflow: {master_entry['id']}")
    print(f"  Total de nós:   {len(unified_nodes)}")
    print(f"  URL n8n: {N8N_URL}/workflow/{master_entry['id']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
