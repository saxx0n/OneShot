#!/usr/bin/env python3

import os
import requests
import yaml
import urllib3

# Tower connection config
TOWER_URL = os.getenv("TOWER_URL") or "https://tower.example.com"
USERNAME = os.getenv("TOWER_USER") or "admin"
PASSWORD = os.getenv("TOWER_PASS") or "password"
API_BASE = f"{TOWER_URL}/api/v2"
AUTH = (USERNAME, PASSWORD)
HEADERS = {"Content-Type": "application/json"}

OUTDIR = os.path.abspath("data_deep_full")
os.makedirs(OUTDIR, exist_ok=True)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Static object map
BASE_ENDPOINTS = {
    "organizations": "organizations",
    "users": "users",
    "teams": "teams",
    "credentials": "credentials",
    "projects": "projects",
    "inventories": "inventories",
    "execution_environments": "execution_environments",
    "schedules": "schedules",
    "workflow_job_templates": "workflow_job_templates",
    "notification_templates": "notification_templates",
    "inventory_sources": "inventory_sources",
}

# Helpers
def fetch_json(path):
    r = requests.get(f"{API_BASE}{path}", auth=AUTH, headers=HEADERS, verify=False)
    r.raise_for_status()
    return r.json()

def fetch_all(path):
    url = f"{API_BASE}{path}"
    results = []
    while url:
        r = requests.get(url, auth=AUTH, headers=HEADERS, verify=False)
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        url = data.get("next")
    return results

def fetch_related_url(url):
    if url.startswith("/api/v2/"):
        url = url[len("/api/v2"):]
    return fetch_all(url)

def fetch_related_json(url):
    if url.startswith("/api/v2/"):
        url = url[len("/api/v2"):]
    return fetch_json(url)

def paginated_ids(endpoint):
    ids = []
    url = f"{API_BASE}/{endpoint}/"
    while url:
        r = requests.get(url, auth=AUTH, headers=HEADERS, verify=False)
        r.raise_for_status()
        data = r.json()
        ids.extend([obj["id"] for obj in data.get("results", [])])
        url = data.get("next")
    return ids

# Enriched job_templates
def extract_job_templates():
    print("▌Extracting job_templates with related fields...")
    job_ids = paginated_ids("job_templates")
    enriched = []

    for job_id in job_ids:
        try:
            jt = fetch_json(f"/job_templates/{job_id}/")
            rel = jt.get("related", {})

            jt["credentials"] = [c["id"] for c in fetch_related_url(rel.get("credentials", ""))] if rel.get("credentials") else []
            jt["survey_spec"] = fetch_related_json(rel["survey_spec"]).get("spec", []) if rel.get("survey_spec") else []

            for nt in ["started", "success", "error"]:
                key = f"notification_templates_{nt}"
                jt[key] = [n["id"] for n in fetch_related_url(rel.get(key, ""))] if rel.get(key) else []

            jt["labels"] = [l["name"] for l in fetch_related_url(rel.get("labels", ""))] if rel.get("labels") else []
            jt["instance_groups"] = [g["name"] for g in fetch_related_url(rel.get("instance_groups", ""))] if rel.get("instance_groups") else []

            enriched.append(jt)

        except Exception as e:
            print(f"[FAIL] job_template {job_id}: {e}")

    with open(os.path.join(OUTDIR, "job_templates.yaml"), "w") as f:
        yaml.dump(enriched, f, default_flow_style=False, sort_keys=False)
    print("✔ Wrote: job_templates.yaml")

# Base object extractor
def extract_base(endpoint, label):
    print(f"▌Extracting {label}...")
    try:
        data = fetch_all(f"/{endpoint}/")
        with open(os.path.join(OUTDIR, f"{label}.yaml"), "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        print(f"✔ Wrote: {label}.yaml")
    except Exception as e:
        print(f"[FAIL] {label}: {e}")

# Entrypoint
def extract_all():
    for label, endpoint in BASE_ENDPOINTS.items():
        extract_base(endpoint, label)
    extract_job_templates()

if __name__ == "__main__":
    extract_all()
