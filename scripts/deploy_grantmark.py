"""Preflight and optionally deploy the GRANTMARK contract on GenLayer StudioNet.

The default action is read-only preflight. Broadcasting requires --deploy.
After a broadcast, retain the printed hash; use --resume-transaction if receipt
polling is interrupted. The deployer has no administrator rights.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path

from eth_account import Account
from eth_utils import to_checksum_address
from genlayer_py import create_client
from genlayer_py.assertions import tx_execution_succeeded
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionHashVariant, TransactionStatus


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "contracts" / "grantmark.py"
TEST_PATH = ROOT / "tests" / "direct" / "test_grantmark.py"
APP_PATH = ROOT / "apps" / "grantmark-web"
MANIFEST_PATH = ROOT / "deployments" / "grantmark_studionet.json"
FRONTEND_ENV = APP_PATH / ".env.local"
ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")
HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")


def source_digest(source: str) -> str:
    return hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def run_preflight() -> None:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    subprocess.run(["genvm-lint", "check", str(SOURCE_PATH)], cwd=ROOT, env=environment, check=True)
    subprocess.run([sys.executable, "-m", "pytest", str(TEST_PATH), "-q"], cwd=ROOT, env=environment, check=True)
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if pnpm is None:
        raise RuntimeError("pnpm is required for frontend preflight")
    subprocess.run([pnpm, "typecheck"], cwd=APP_PATH, env=environment, check=True)
    subprocess.run([pnpm, "build"], cwd=APP_PATH, env=environment, check=True)
    subprocess.run([pnpm, "audit", "--prod", "--audit-level", "high"], cwd=APP_PATH, env=environment, check=True)


def assert_finalized_success(receipt: dict) -> None:
    status = receipt.get("status_name") or receipt.get("statusName")
    if status != TransactionStatus.FINALIZED.value or not tx_execution_succeeded(receipt):
        raise RuntimeError("deployment did not finalize with successful execution")


def deployed_address(receipt: dict) -> str:
    for key in ("tx_data_decoded", "data"):
        payload = receipt.get(key)
        if isinstance(payload, dict) and payload.get("contract_address"):
            result = str(payload["contract_address"])
            if ADDRESS.fullmatch(result) is None or int(result[2:], 16) == 0:
                raise RuntimeError("deployment receipt contained an invalid address")
            return to_checksum_address(result)
    raise RuntimeError("deployment receipt did not expose the contract address")


def verify_deployed_source(client, address: str, source: str) -> None:
    result = client.provider.make_request(method="gen_getContractCode", params=[address]).get("result")
    if not isinstance(result, str):
        raise RuntimeError("could not read the deployed contract source")
    try:
        actual = base64.b64decode(result, validate=True).decode("utf-8")
    except (ValueError, UnicodeError):
        raise RuntimeError("deployed source was not valid encoded Python") from None
    if source_digest(actual) != source_digest(source):
        raise RuntimeError("deployed source differs from the tested local source")


def verify_config(client, address: str, account) -> dict:
    config = client.read_contract(
        address=address,
        function_name="get_config",
        args=[],
        account=account,
        transaction_hash_variant=TransactionHashVariant.LATEST_FINAL,
    )
    expected = {
        "version": "0.1.0",
        "network": "STUDIONET",
        "funding": "DEPOSIT_THEN_SPEND_WITH_RECOVERABLE_CREDIT",
        "adjudication_timeout_secs": str(7 * 86400),
        "settlement": "MET_TO_BENEFICIARY; ALL_OTHER_OUTCOMES_TO_SPONSOR",
    }
    if not isinstance(config, dict) or any(config.get(key) != value for key, value in expected.items()):
        raise RuntimeError("deployed configuration differs from the GRANTMARK release")
    return config


def write_atomic(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix="grantmark-", suffix=".tmp", delete=False) as temporary:
        temporary.write(body)
        staged = Path(temporary.name)
    staged.replace(path)


def save_release(record: dict) -> None:
    if MANIFEST_PATH.exists():
        prior = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if prior.get("address", "").lower() != record["address"].lower():
            raise RuntimeError("a different GRANTMARK deployment is already recorded; archive it before replacing the release")
    write_atomic(MANIFEST_PATH, json.dumps(record, indent=2) + "\n")
    lines = FRONTEND_ENV.read_text(encoding="utf-8").splitlines() if FRONTEND_ENV.exists() else []
    lines = [line for line in lines if not line.startswith("NEXT_PUBLIC_GRANTMARK_ADDRESS=")]
    lines.append("NEXT_PUBLIC_GRANTMARK_ADDRESS=" + record["address"])
    write_atomic(FRONTEND_ENV, "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--deploy", action="store_true", help="broadcast one StudioNet deployment after preflight")
    actions.add_argument("--resume-transaction", help="verify an already-broadcast deployment hash")
    parser.add_argument("--ephemeral-studionet-deployer", action="store_true", help="use a disposable StudioNet-only deployment signer")
    args = parser.parse_args()
    if args.resume_transaction and HASH.fullmatch(args.resume_transaction) is None:
        parser.error("--resume-transaction requires a 32-byte transaction hash")
    if args.ephemeral_studionet_deployer and not args.deploy:
        parser.error("--ephemeral-studionet-deployer requires --deploy")
    if args.deploy and MANIFEST_PATH.exists():
        raise RuntimeError("an GRANTMARK deployment is already recorded; review or archive it before broadcasting another")
    if not args.resume_transaction:
        run_preflight()
    source = SOURCE_PATH.read_text(encoding="utf-8")
    print("source_sha256=" + source_digest(source), flush=True)
    if not (args.deploy or args.resume_transaction):
        print("preflight_passed=true; no transaction was broadcast", flush=True)
        return

    if args.resume_transaction:
        account = Account.create()  # Read-only context; never signs or broadcasts.
        signer_mode = "resumed_existing_transaction"
    elif args.ephemeral_studionet_deployer:
        account = Account.create()
        signer_mode = "disposable_studionet_deployment_only"
    else:
        secret = os.environ.get("GRANTMARK_PRIVATE_KEY") or getpass("Dedicated GRANTMARK deployer key (hidden): ").strip()
        if not secret:
            raise RuntimeError("a deployment key is required")
        try:
            account = Account.from_key(secret)
        except (TypeError, ValueError):
            raise RuntimeError("deployment key format is invalid") from None
        del secret
        signer_mode = "dedicated_recoverable_signer"

    client = create_client(chain=studionet, account=account)
    transaction_hash = args.resume_transaction or client.deploy_contract(code=source, account=account, args=[])
    print("transaction=" + str(transaction_hash), flush=True)
    receipt = client.wait_for_transaction_receipt(
        transaction_hash=transaction_hash,
        status=TransactionStatus.FINALIZED,
        interval=3000,
        retries=120,
        full_transaction=True,
    )
    assert_finalized_success(receipt)
    address = deployed_address(receipt)
    verify_deployed_source(client, address, source)
    config = verify_config(client, address, account)
    deployer = str(receipt.get("from_address") or receipt.get("from") or "")
    if ADDRESS.fullmatch(deployer) is None:
        raise RuntimeError("finalized deployment receipt did not identify the deployer")
    record = {
        "contract": "Grantmark",
        "version": "0.1.0",
        "network": "studionet",
        "address": address,
        "transaction_hash": str(transaction_hash),
        "deployer": to_checksum_address(deployer),
        "deployer_role": "no_admin_controls_or_protocol_fees",
        "signer_mode": signer_mode,
        "constructor_args": [],
        "source_sha256": source_digest(source),
        "runner_dependency": source.splitlines()[0],
        "receipt_status": "FINALIZED",
        "execution_result": "SUCCESS",
        "verified_source_and_config": True,
        "preflight_passed": not bool(args.resume_transaction),
        "config": config,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    save_release(record)
    print("verified_deployment=" + address, flush=True)
    print("record=" + str(MANIFEST_PATH), flush=True)
    print("frontend_env=" + str(FRONTEND_ENV), flush=True)


if __name__ == "__main__":
    main()
