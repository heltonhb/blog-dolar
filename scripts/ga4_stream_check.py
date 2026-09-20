#!/usr/bin/env python3
"""Confirma o measurement ID do data stream web da propriedade GA4 554549804."""
import json
import sys
import urllib.request

sys.path.insert(0, "scripts")
from check_indexacao import get_access_token


def main():
    token, _ = get_access_token("analytics.readonly")
    hdr = {"Authorization": f"Bearer {token}"}

    # Data streams da propriedade
    url = "https://analyticsadmin.googleapis.com/v1beta/properties/554549804/dataStreams"
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    for s in data.get("dataStreams", []):
        wt = s.get("webStreamData", {})
        print(f"stream: {s.get('displayName')} | type: {s.get('streamType')}")
        print(f"  measurementId: {wt.get('measurementId')}")
        print(f"  defaultUri: {wt.get('defaultUri')}")

    # Nome da propriedade
    req = urllib.request.Request(
        "https://analyticsadmin.googleapis.com/v1beta/properties/554549804", headers=hdr
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        prop = json.loads(r.read())
    print(f"propriedade: {prop.get('displayName')}")


if __name__ == "__main__":
    main()
