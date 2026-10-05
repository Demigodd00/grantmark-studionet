"""Read-only verification of the public GRANTMARK StudioNet release."""

from __future__ import annotations

import json
import hashlib
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


def amount(value) -> int:
    return int(value, 16) if isinstance(value, str) and value.startswith("0x") else int(value)


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

    finished = journal["status"] == "SETTLED_AND_WITHDRAWN"
    if journal["status"] not in ("SUBMITTED_AWAITING_REVIEW_DEADLINE", "SETTLED_AND_WITHDRAWN"):
        raise RuntimeError("unknown acceptance status")
    checked_names = ("deposit", "create", "submit", "resolve", "withdraw") if finished else ("deposit", "create", "submit")
    for name in checked_names:
        entry = journal["transactions"][name]
        if entry.get("state") != "checked" or entry.get("final_status") != "FINALIZED":
            raise RuntimeError(f"{name}: journal did not record a finalized successful write")
        receipt = rpc("eth_getTransactionByHash", [entry["hash"]])
        if not isinstance(receipt, dict) or receipt.get("status") != "FINALIZED" or not tx_execution_succeeded(receipt):
            raise RuntimeError(f"{name}: not a finalized successful transaction")
        if receipt.get("from_address", "").lower() != entry["sender"].lower():
            raise RuntimeError(f"{name}: sender mismatch")
        if receipt.get("to_address", "").lower() != address.lower():
            raise RuntimeError(f"{name}: contract destination mismatch")
        if amount(receipt.get("value", 0)) != int(entry["value_atto"]):
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
    if finished:
        if grant["status"] != "SETTLED" or grant["outcome"] not in ("MET", "NOT_MET", "INCONCLUSIVE"):
            raise RuntimeError("sample has no finalized adjudication")
        recipient = grant["beneficiary"] if grant["outcome"] == "MET" else grant["sponsor"]
        if grant["settlement_recipient"].lower() != recipient.lower():
            raise RuntimeError("settlement recipient contradicts the outcome")
        settlement = journal["settlement"]
        for key in ("outcome", "reason", "settled_at", "citations"):
            if settlement[key] != grant[key]:
                raise RuntimeError(f"recorded {key} differs from finalized state")
        if settlement["recipient"].lower() != recipient.lower():
            raise RuntimeError("recorded recipient differs from finalized state")
        sources = {source["id"]: source for source in grant["evidence_snapshot"]}
        for source in sources.values():
            if source["status"] == "READABLE" and hashlib.sha256(source["text"].encode("utf-8")).hexdigest() != source["digest"]:
                raise RuntimeError("stored evidence digest is invalid")
        for citation in grant["citations"]:
            source = sources.get(citation["source_id"])
            if source is None or source["status"] != "READABLE":
                raise RuntimeError("citation refers to an unreadable source")
            lines = source["text"].splitlines()
            line = citation["line"]
            if (type(line) is not int or line < 1 or line > len(lines)
                    or citation["excerpt"] != lines[line - 1]
                    or citation["digest"] != source["digest"]
                    or citation["url"] != source["url"]):
                raise RuntimeError("citation does not match the stored source")
        if int(read(client, address, "get_credit", [recipient])) != 0:
            raise RuntimeError("winner credit did not clear after withdrawal")
        if int(stats["total_locked_atto"]) != 0 or int(stats["total_settled_atto"]) < int(grant["tranche_atto"]):
            raise RuntimeError("settlement totals do not account for the tranche")
        proof = journal["withdrawal_proof"]
        parent = rpc("eth_getTransactionByHash", [journal["transactions"]["withdraw"]["hash"]])
        if parent.get("triggered_transactions") != [proof["child_hash"]] or proof["parent_hash"] != journal["transactions"]["withdraw"]["hash"]:
            raise RuntimeError("withdrawal parent does not name the recorded native transfer")
        child = rpc("eth_getTransactionByHash", [proof["child_hash"]])
        if (not child or child.get("status") != "FINALIZED" or child.get("value_credited") is not True
                or child.get("from_address", "").lower() != address.lower()
                or child.get("to_address", "").lower() != recipient.lower()
                or amount(child.get("value", 0)) != int(grant["tranche_atto"])):
            raise RuntimeError("native transfer did not credit the exact tranche")
        if (proof["recipient"].lower() != recipient.lower() or proof["value_credited"] is not True
                or int(proof["amount_atto"]) != int(grant["tranche_atto"])
                or int(proof["balance_after_atto"]) - int(proof["balance_before_atto"]) != int(grant["tranche_atto"])):
            raise RuntimeError("withdrawal journal contradicts the native transfer")
    elif grant["status"] != "SUBMITTED":
        raise RuntimeError("acceptance status differs from finalized grant state")

    site = requests.get(journal["frontend"], timeout=30)
    evidence = requests.get(grant["evidence_urls"][0], timeout=30)
    site.raise_for_status()
    evidence.raise_for_status()
    if "GRANTMARK" not in site.text or "SYNTHETIC ACCEPTANCE FIXTURE" not in evidence.text:
        raise RuntimeError("public app or disclosed synthetic evidence is unavailable")
    print(json.dumps({"verified": True, "address": address, "grant_id": grant["id"],
                      "status": grant["status"], "outcome": grant["outcome"],
                      "checked_transactions": [journal["transactions"][name]["hash"] for name in checked_names],
                      "native_withdrawals": 1 if finished else 0}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"verification_failed={error}", file=sys.stderr)
        raise SystemExit(1)
