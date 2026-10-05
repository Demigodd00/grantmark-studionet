"""Read-only verification of the public GRANTMARK StudioNet release."""

from __future__ import annotations

import json
import sys

import requests
from eth_account import Account
from genlayer_py import create_client
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionHashVariant

from deploy_grantmark import ROOT, source_digest, verify_config, verify_deployed_source

RPC = "https://studio.genlayer.com/api"
MANIFEST = ROOT / "deployments" / "grantmark_studionet.json"
JOURNAL = ROOT / "deployments" / "grantmark_acceptance.json"


def rpc(method: str, params: list):
    response = requests.post(RPC, json={"jsonrpc": "2.0", "id": 1,
                                        "method": method, "params": params}, timeout=(10, 60))
    response.raise_for_status()
    body = response.json()
    if body.get("error"):
        raise RuntimeError(f"{method}: {body['error']}")
    return body["result"]


def read(client, address: str, method: str, args: list):
    return client.read_contract(address=address, function_name=method, args=args,
                                transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    journal = json.loads(JOURNAL.read_text(encoding="utf-8"))
    address = manifest["address"]
    if journal["contract"].lower() != address.lower():
        raise RuntimeError("acceptance journal names a different contract")
    source = (ROOT / "contracts" / "grantmark.py").read_text(encoding="utf-8")
    if source_digest(source) != manifest["source_sha256"]:
        raise RuntimeError("local source differs from the deployed release")
    client = create_client(chain=studionet, account=Account.create())
    verify_deployed_source(client, address, source)
    verify_config(client, address, client.local_account)

    for name in ("deposit", "create", "submit"):
        entry = journal["transactions"][name]
        receipt = rpc("eth_getTransactionByHash", [entry["hash"]])
        if not isinstance(receipt, dict) or receipt.get("status") != "FINALIZED" or not tx_execution_succeeded(receipt):
            raise RuntimeError(f"{name}: not a finalized successful transaction")
        if receipt.get("from_address", "").lower() != entry["sender"].lower():
            raise RuntimeError(f"{name}: sender mismatch")
        if receipt.get("to_address", "").lower() != address.lower():
            raise RuntimeError(f"{name}: contract destination mismatch")
        if int(receipt.get("value", 0)) != int(entry["value_atto"]):
            raise RuntimeError(f"{name}: transaction value mismatch")

    grant = read(client, address, "get_grant", [journal["grant_id"]])
    if grant["sponsor"].lower() != journal["wallets"]["sponsor"].lower():
        raise RuntimeError("grant sponsor mismatch")
    if grant["beneficiary"].lower() != journal["wallets"]["beneficiary"].lower():
        raise RuntimeError("grant beneficiary mismatch")
    if grant["evidence_urls"] != [journal["frontend"] + "/evidence/demo-register.txt"]:
        raise RuntimeError("submitted evidence URL mismatch")
    if int(grant["tranche_atto"]) != 4 * 10**15:
        raise RuntimeError("tranche amount mismatch")
    stats = read(client, address, "get_stats", [])
    if grant["status"] == "SUBMITTED" and int(stats["total_locked_atto"]) < int(grant["tranche_atto"]):
        raise RuntimeError("submitted grant tranche is not locked")
    if grant["status"] == "SETTLED" and grant["settlement_recipient"] not in (grant["sponsor"], grant["beneficiary"]):
        raise RuntimeError("settled recipient is not a grant party")

    site = requests.get(journal["frontend"], timeout=30)
    evidence = requests.get(grant["evidence_urls"][0], timeout=30)
    site.raise_for_status()
    evidence.raise_for_status()
    if "GRANTMARK" not in site.text or "SYNTHETIC ACCEPTANCE FIXTURE" not in evidence.text:
        raise RuntimeError("public app or disclosed synthetic evidence is unavailable")
    print(json.dumps({"verified": True, "address": address, "grant_id": grant["id"],
                      "status": grant["status"], "outcome": grant["outcome"],
                      "checked_transactions": [journal["transactions"][name]["hash"] for name in ("deposit", "create", "submit")]}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"verification_failed={error}", file=sys.stderr)
        raise SystemExit(1)
