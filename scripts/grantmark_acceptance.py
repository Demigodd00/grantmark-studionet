"""Create a synthetic, publicly reviewable StudioNet grant without exposing wallet keys.

The journal is written before each broadcast. If a write is interrupted after
broadcast but before its GenLayer hash is saved, this script stops rather than
resending a financial transaction. Inspect wallet activity in that case.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from eth_account import Account
from genlayer_py import create_client
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionHashVariant, TransactionStatus

from deploy_grantmark import ROOT, write_atomic

DEPLOYMENT = ROOT / "deployments" / "grantmark_studionet.json"
JOURNAL = ROOT / "deployments" / "grantmark_acceptance.json"
KEYS = Path.home() / ".codex" / "private" / "grantmark_acceptance_wallets.json"
ORIGIN = "https://grantmark-web.vercel.app"
RPC = "https://studio.genlayer.com/api"
TRANCHE = 4 * 10**15


def rpc(method: str, params: list) -> dict:
    response = requests.post(RPC, json={"jsonrpc": "2.0", "id": int(time.time() * 1000),
                                        "method": method, "params": params}, timeout=(10, 60))
    response.raise_for_status()
    body = response.json()
    if body.get("error"):
        raise RuntimeError(f"{method}: {body['error']}")
    return body["result"]


def save(record: dict) -> None:
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_atomic(JOURNAL, json.dumps(record, indent=2) + "\n")


def wallet_keys() -> dict:
    if not KEYS.exists():
        if JOURNAL.exists():
            raise RuntimeError("Acceptance journal exists but original wallets are missing")
        KEYS.parent.mkdir(parents=True, exist_ok=True)
        with KEYS.open("x", encoding="utf-8") as handle:
            json.dump({role: Account.create().key.hex() for role in ("sponsor", "beneficiary")}, handle)
    return {role: Account.from_key(key) for role, key in json.loads(KEYS.read_text(encoding="utf-8")).items()}


def read(client, contract: str, name: str, args: list):
    return client.read_contract(address=contract, function_name=name, args=args,
                                transaction_hash_variant=TransactionHashVariant.LATEST_FINAL)


def write_step(record: dict, client, contract: str, step: str, name: str, args: list, account, value: int = 0) -> None:
    intent = {"method": name, "args": args, "sender": account.address, "value_atto": str(value)}
    entry = record["transactions"].get(step)
    if entry is None:
        entry = {**intent, "state": "prepared"}
        record["transactions"][step] = entry
        save(record)
    if any(entry.get(key) != expected for key, expected in intent.items()):
        raise RuntimeError(f"{step}: saved transaction intent changed")
    if entry.get("state") == "checked":
        return
    if entry.get("state") == "broadcasting" and not entry.get("hash"):
        raise RuntimeError(f"{step}: broadcast outcome is uncertain; inspect wallet history, do not resend")
    if not entry.get("hash"):
        entry["state"] = "broadcasting"
        save(record)
        tx_hash = client.write_contract(address=contract, function_name=name, args=args,
                                        account=account, value=value)
        entry["hash"] = str(tx_hash)
        entry["state"] = "submitted"
        save(record)
        print(f"{step}: submitted {tx_hash}", flush=True)
    receipt = client.wait_for_transaction_receipt(transaction_hash=entry["hash"],
                                                  status=TransactionStatus.FINALIZED,
                                                  interval=3000, retries=120,
                                                  full_transaction=True)
    status = receipt.get("status_name") or receipt.get("statusName")
    if status != TransactionStatus.FINALIZED.value or not tx_execution_succeeded(receipt):
        entry["state"] = "failed_or_unfinalized"
        save(record)
        raise RuntimeError(f"{step}: transaction was not finalized with successful execution")
    entry["state"] = "checked"
    entry["final_status"] = status
    save(record)
    print(f"{step}: finalized", flush=True)


def main() -> None:
    deployment = json.loads(DEPLOYMENT.read_text(encoding="utf-8"))
    contract = deployment["address"]
    wallets = wallet_keys()
    addresses = {role: account.address for role, account in wallets.items()}
    record = json.loads(JOURNAL.read_text(encoding="utf-8")) if JOURNAL.exists() else {
        "network": "studionet", "contract": contract, "frontend": ORIGIN,
        "wallets": addresses, "transactions": {}, "checks": {},
        "fixture_disclosure": "The public delivery register is synthetic and controlled by GRANTMARK. It is not proof of a real grant distribution.",
    }
    if record["contract"] != contract or record["wallets"] != addresses:
        raise RuntimeError("Acceptance journal does not match this release")
    save(record)
    page = requests.get(ORIGIN, timeout=30)
    fixture = requests.get(ORIGIN + "/evidence/demo-register.txt", timeout=30)
    page.raise_for_status()
    fixture.raise_for_status()
    if "GRANTMARK" not in page.text or "100 distinct recipient IDs" not in fixture.text:
        raise RuntimeError("Public app or synthetic evidence fixture is not live")
    record["checks"]["public_site_and_fixture"] = True
    save(record)

    for role, account in wallets.items():
        balance = rpc("eth_getBalance", [account.address, "latest"])
        balance = int(balance, 16) if isinstance(balance, str) and balance.startswith("0x") else int(balance)
        if balance < 10**17:
            rpc("sim_fundAccount", [account.address, 10**18])
        funded = rpc("eth_getBalance", [account.address, "latest"])
        funded = int(funded, 16) if isinstance(funded, str) and funded.startswith("0x") else int(funded)
        if funded < 10**17:
            raise RuntimeError(f"StudioNet test funding did not credit {role}")
        record["checks"]["funded_" + role] = True
        save(record)

    sponsor = wallets["sponsor"]
    beneficiary = wallets["beneficiary"]
    client = create_client(chain=studionet, account=sponsor)
    write_step(record, client, contract, "deposit", "deposit", [], sponsor, TRANCHE)
    credit = int(read(client, contract, "get_credit", [sponsor.address]))
    if record["transactions"].get("create", {}).get("state") != "checked" and credit != TRANCHE:
        raise RuntimeError(f"deposit credit mismatch: {credit}")
    record["checks"]["deposit_credit_confirmed"] = True
    save(record)

    title = "GRANTMARK synthetic kit delivery " + contract[2:10]
    args = [
        title,
        "Deliver 100 school kits to 100 distinct recipient IDs and publish a dated delivery register.",
        "MET only if the dated public register establishes 100 delivered kits and 100 distinct recipient IDs; NOT_MET if a public audit establishes fewer; otherwise INCONCLUSIVE.",
        beneficiary.address,
        3600, 3600, TRANCHE,
    ]
    write_step(record, client, contract, "create", "create_grant", args, sponsor)
    page = read(client, contract, "list_grants", [0, 50])
    matches = [item for item in page["items"] if item["title"] == title and item["sponsor"].lower() == sponsor.address.lower()]
    if len(matches) != 1:
        raise RuntimeError("finalized grant was not found exactly once")
    grant_id = matches[0]["id"]
    record["grant_id"] = grant_id
    grant = read(client, contract, "get_grant", [grant_id])
    if grant["status"] not in ("OPEN", "SUBMITTED") or grant["beneficiary"].lower() != beneficiary.address.lower():
        raise RuntimeError("created grant terms differ from acceptance intent")
    record["checks"]["grant_created"] = True
    save(record)

    write_step(record, client, contract, "submit", "submit_evidence", [
        grant_id,
        "The synthetic dated register records 100 delivered school kits and 100 distinct recipient IDs.",
        json.dumps([ORIGIN + "/evidence/demo-register.txt"]),
    ], beneficiary)
    grant = read(client, contract, "get_grant", [grant_id])
    if grant["status"] != "SUBMITTED" or grant["evidence_urls"] != [ORIGIN + "/evidence/demo-register.txt"]:
        raise RuntimeError("finalized evidence submission was not recorded")
    if int(read(client, contract, "get_stats", [])["total_locked_atto"]) != TRANCHE:
        raise RuntimeError("tranche is not locked after evidence submission")
    record["checks"]["evidence_submitted_and_tranche_locked"] = True
    record["status"] = "SUBMITTED_AWAITING_REVIEW_DEADLINE"
    record["review_deadline"] = grant["review_deadline"]
    record["reviewer_note"] = "This acceptance run proves finalized funding, grant creation, submission, and locked tranche. Live adjudication and withdrawal remain unverified until the review deadline."
    save(record)
    print(json.dumps({"grant_id": grant_id, "status": record["status"],
                      "review_deadline": grant["review_deadline"], "journal": str(JOURNAL)}), flush=True)


if __name__ == "__main__":
    main()
