"""Escrow safety and validator evidence checks for GRANTMARK."""

import json
import sys
from datetime import datetime, timezone

import pytest

TRANCHE = 4 * 10**15
EVIDENCE_URL = "https://example.org/grantmark-report"
OBJECTION_URL = "https://example.net/grantmark-audit"
EVIDENCE_BODY = "Milestone delivery register: 100 kits delivered to 100 distinct recipient IDs.\nDelivery date: 2026-10-01."
OBJECTION_BODY = "Independent audit: only 90 kits reached distinct recipients.\nTen records have duplicate IDs."


def address(account):
    return "0x" + bytes(account).hex()


def warp(vm, timestamp):
    value = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    vm.warp(value)
    gl = sys.modules.get("genlayer.gl")
    assert gl is not None
    gl.message_raw["datetime"] = value


def create(vm, deploy, sponsor, beneficiary):
    contract = deploy("contracts/grantmark.py")
    vm.sender = sponsor
    vm.value = TRANCHE
    contract.deposit()
    vm.value = 0
    grant_id = contract.create_grant(
        "School kit pilot",
        "Deliver 100 kits to 100 distinct recipient IDs by the milestone deadline.",
        "MET only if a dated delivery register establishes 100 distinct recipients and 100 delivered kits; NOT_MET if an audit establishes fewer; otherwise INCONCLUSIVE.",
        address(beneficiary),
        3600,
        3600,
        TRANCHE,
    )
    return contract, grant_id


def submit(vm, contract, grant_id, beneficiary):
    vm.sender = beneficiary
    contract.submit_evidence(
        grant_id,
        "The dated delivery register records 100 kits delivered to 100 unique recipient IDs.",
        json.dumps([EVIDENCE_URL]),
    )


def mock_decision(vm, outcome="MET", body=EVIDENCE_BODY):
    vm.mock_web(EVIDENCE_URL, {"status": 200, "body": body})
    vm.mock_web(OBJECTION_URL, {"status": 200, "body": OBJECTION_BODY})
    vm.mock_llm(
        r".*independent GenLayer adjudicator for GRANTMARK.*",
        json.dumps({
            "outcome": outcome,
            "reason": "The cited public record establishes the result under the locked delivery rubric.",
            "citations": [] if outcome == "INCONCLUSIVE" else [{"source_id": "S1", "line": 1}],
        }),
    )


@pytest.mark.parametrize("outcome,beneficiary_wins", [("MET", True), ("NOT_MET", False), ("INCONCLUSIVE", False)])
def test_adjudication_settles_exactly_once(direct_vm, direct_deploy, direct_alice, direct_bob, outcome, beneficiary_wins):
    contract, grant_id = create(direct_vm, direct_deploy, direct_alice, direct_bob)
    submit(direct_vm, contract, grant_id, direct_bob)
    warp(direct_vm, int(contract.get_grant(grant_id)["review_deadline"]) + 1)
    mock_decision(direct_vm, outcome)
    contract.resolve(grant_id)
    assert direct_vm.run_validator()
    grant = contract.get_grant(grant_id)
    assert grant["outcome"] == outcome
    assert grant["settlement_recipient"] == address(direct_bob if beneficiary_wins else direct_alice)
    assert int(contract.get_credit(grant["settlement_recipient"])) == TRANCHE
    assert int(contract.get_stats()["total_locked_atto"]) == 0
    assert int(contract.get_stats()["total_settled_atto"]) == TRANCHE
    with pytest.raises(Exception, match="only a submitted grant"):
        contract.resolve(grant_id)
    direct_vm.sender = direct_bob if beneficiary_wins else direct_alice
    contract.withdraw_credit()
    assert int(contract.get_credit(grant["settlement_recipient"])) == 0


def test_no_submission_refunds_and_cannot_later_submit(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract, grant_id = create(direct_vm, direct_deploy, direct_alice, direct_bob)
    with pytest.raises(Exception, match="after its deadline"):
        contract.expire_unsubmitted(grant_id)
    warp(direct_vm, int(contract.get_grant(grant_id)["submission_deadline"]) + 1)
    contract.expire_unsubmitted(grant_id)
    assert contract.get_grant(grant_id)["outcome"] == "NO_SUBMISSION"
    assert int(contract.get_credit(address(direct_alice))) == TRANCHE
    with pytest.raises(Exception, match="not accepting a submission"):
        submit(direct_vm, contract, grant_id, direct_bob)


def test_timeout_refunds_without_model(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract, grant_id = create(direct_vm, direct_deploy, direct_alice, direct_bob)
    submit(direct_vm, contract, grant_id, direct_bob)
    warp(direct_vm, int(contract.get_grant(grant_id)["review_deadline"]) + 7 * 86400 + 1)
    direct_vm.sender = direct_bob
    contract.expire_unresolved(grant_id)
    assert contract.get_grant(grant_id)["outcome"] == "TIMEOUT_REFUND"
    assert int(contract.get_credit(address(direct_alice))) == TRANCHE
    assert int(contract.get_stats()["total_locked_atto"]) == 0


def test_only_beneficiary_submits_and_sponsor_objects_once(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract, grant_id = create(direct_vm, direct_deploy, direct_alice, direct_bob)
    with pytest.raises(Exception, match="only the beneficiary"):
        contract.submit_evidence(grant_id, "This report is valid and long enough to submit.", json.dumps([EVIDENCE_URL]))
    submit(direct_vm, contract, grant_id, direct_bob)
    with pytest.raises(Exception, match="only the sponsor"):
        contract.object_to_evidence(grant_id, "Audit disputes the reported distinct recipient count.", OBJECTION_URL)
    direct_vm.sender = direct_alice
    contract.object_to_evidence(grant_id, "Audit disputes the reported distinct recipient count.", OBJECTION_URL)
    with pytest.raises(Exception, match="already been submitted"):
        contract.object_to_evidence(grant_id, "A second audit disputes the recipient count.", OBJECTION_URL)


def test_validator_rejects_edited_evidence(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract, grant_id = create(direct_vm, direct_deploy, direct_alice, direct_bob)
    submit(direct_vm, contract, grant_id, direct_bob)
    warp(direct_vm, int(contract.get_grant(grant_id)["review_deadline"]) + 1)
    mock_decision(direct_vm)
    contract.resolve(grant_id)
    direct_vm.clear_mocks()
    mock_decision(direct_vm, body="Edited register: only 90 kits delivered to distinct recipient IDs.\nAudit is in progress.")
    assert not direct_vm.run_validator()


def test_failed_create_keeps_deposit_withdrawable(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy("contracts/grantmark.py")
    direct_vm.sender = direct_alice
    direct_vm.value = TRANCHE
    contract.deposit()
    direct_vm.value = 0
    with pytest.raises(Exception, match="rubric"):
        contract.create_grant("School kit pilot", "Deliver 100 kits to 100 recipients.", "Too short", address(direct_bob), 3600, 3600, TRANCHE)
    assert int(contract.get_credit(address(direct_alice))) == TRANCHE
    assert contract.get_stats()["total_created"] == "0"
