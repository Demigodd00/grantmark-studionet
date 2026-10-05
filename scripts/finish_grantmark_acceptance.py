"""After the real review deadline, finish the synthetic GRANTMARK sample.

Resumes saved transaction hashes and never resends an uncertain broadcast.
Only test-GEN wallets held outside the repository are used.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from genlayer_py import create_client
from genlayer_py.chains import studionet

from grantmark_acceptance import JOURNAL, KEYS, read, rpc, save, wallet_keys, write_step


def amount(value) -> int:
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return int(value)


def main() -> None:
    if not KEYS.exists() or not JOURNAL.exists():
        raise RuntimeError("Original acceptance wallets and journal are required")
    record = json.loads(JOURNAL.read_text(encoding="utf-8"))
    if int(time.time()) < int(record["review_deadline"]):
        deadline = datetime.fromtimestamp(int(record["review_deadline"]), timezone.utc).isoformat()
        raise RuntimeError(f"Wait for the real review deadline ({deadline}); no time override is used")
    wallets = wallet_keys()
    contract = record["contract"]
    client = create_client(chain=studionet, account=wallets["sponsor"])
    grant_id = record["grant_id"]
    grant = read(client, contract, "get_grant", [grant_id])
    if grant["status"] == "SUBMITTED" or "resolve" in record["transactions"]:
        write_step(record, client, contract, "resolve", "resolve", [grant_id], wallets["sponsor"])
        grant = read(client, contract, "get_grant", [grant_id])
    if grant["status"] != "SETTLED" or grant["outcome"] not in ("MET", "NOT_MET", "INCONCLUSIVE"):
        raise RuntimeError("Sample did not settle through GenLayer adjudication")
    winner = "beneficiary" if grant["outcome"] == "MET" else "sponsor"
    account = wallets[winner]
    if grant["settlement_recipient"].lower() != account.address.lower():
        raise RuntimeError("settlement recipient contradicts the contract rule")
    tranche = int(grant["tranche_atto"])
    credit = int(read(client, contract, "get_credit", [account.address]))
    if "withdraw" not in record["transactions"] and credit != tranche:
        raise RuntimeError("winner was not credited the exact tranche")
    record["checks"]["genlayer_verdict_and_credit"] = {"outcome": grant["outcome"], "recipient": account.address,
                                                          "amount_atto": str(tranche), "citations": grant["citations"]}
    record["settlement"] = {"outcome": grant["outcome"], "reason": grant["reason"],
                            "recipient": account.address, "settled_at": grant["settled_at"],
                            "citations": grant["citations"]}
    save(record)
    if "withdraw_balance_before_atto" not in record:
        record["withdraw_balance_before_atto"] = str(amount(rpc("eth_getBalance", [account.address, "latest"])))
        save(record)
    write_step(record, client, contract, "withdraw", "withdraw_credit", [], account)
    if int(read(client, contract, "get_credit", [account.address])) != 0:
        raise RuntimeError("winner credit did not clear after withdrawal")
    parent = rpc("eth_getTransactionByHash", [record["transactions"]["withdraw"]["hash"]])
    children = parent.get("triggered_transactions", [])
    if len(children) != 1:
        raise RuntimeError("withdrawal did not create exactly one native transfer")
    child = None
    for _ in range(30):
        child = rpc("eth_getTransactionByHash", [children[0]])
        if child and child.get("status") == "FINALIZED":
            break
        time.sleep(5)
    if not child or child.get("value_credited") is not True:
        raise RuntimeError("native child transfer was not finalized and credited")
    if child.get("from_address", "").lower() != contract.lower() or child.get("to_address", "").lower() != account.address.lower():
        raise RuntimeError("native transfer sender or recipient mismatch")
    if amount(child.get("value", 0)) != tranche:
        raise RuntimeError("native transfer amount mismatch")
    after = amount(rpc("eth_getBalance", [account.address, "latest"]))
    before = int(record["withdraw_balance_before_atto"])
    if after - before != tranche:
        raise RuntimeError("recipient wallet balance did not increase by the exact tranche")
    record["withdrawal_proof"] = {"parent_hash": record["transactions"]["withdraw"]["hash"],
                                   "child_hash": children[0], "recipient": account.address,
                                   "amount_atto": str(tranche), "value_credited": True,
                                   "balance_before_atto": str(before), "balance_after_atto": str(after)}
    record["status"] = "SETTLED_AND_WITHDRAWN"
    record["checks"]["withdrawal_exact_transfer"] = True
    record["reviewer_note"] = "Finalized GenLayer adjudication and an exact native test-GEN withdrawal are independently verifiable from the recorded parent and child transactions. The submitted register is synthetic, not proof of a real grant distribution."
    save(record)
    print(json.dumps({"status": record["status"], "grant_id": grant_id,
                      "outcome": grant["outcome"], "recipient": account.address,
                      "withdrawal_child_hash": children[0]}), flush=True)


if __name__ == "__main__":
    main()
