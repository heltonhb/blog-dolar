#!/usr/bin/env python3
"""Diagnóstico DNS da migração techtips.dpdns.org (arquivo, sem inline)."""
import json
import subprocess


def dns_google(name: str, rtype: str) -> dict:
    r = subprocess.run(
        ["curl", "-s", f"https://dns.google/resolve?name={name}&type={rtype}", "--max-time", "20"],
        capture_output=True, text=True,
    )
    return json.loads(r.stdout or "{}")


print("── 1. Delegação NS vista pelo mundo ──")
d = dns_google("techtips.dpdns.org", "NS")
print("Status:", d.get("Status"), "| Comment:", d.get("Comment", ""))
for a in d.get("Answer", []) or []:
    print("  NS:", a.get("data"))

print("\n── 2. Direto no nameserver da InfinityFree ──")
r = subprocess.run(
    ["curl", "-s", "https://dns.google/resolve?name=techtips.dpdns.org&type=A", "--max-time", "20"],
    capture_output=True, text=True,
)
d2 = json.loads(r.stdout or "{}")
print("A record Status:", d2.get("Status"))
for a in d2.get("Answer", []) or []:
    print("  A:", a.get("data"))
if d2.get("Comment"):
    print("  Comment:", d2.get("Comment"))
