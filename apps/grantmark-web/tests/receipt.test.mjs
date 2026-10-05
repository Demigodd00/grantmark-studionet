import assert from "node:assert/strict";
import { test } from "node:test";
import { assertSuccessfulExecution, depositHistoryCandidates, transactionStatus } from "../src/lib/grantmark.ts";

const execution = {
  consensus_data: {
    leader_receipt: [{
      execution_result: "SUCCESS",
      result: { status: "return", payload: { readable: "null" } },
      genvm_result: { error_code: null, error_description: null },
    }],
  },
};

test("accepts finalized simplified and full receipts", () => {
  for (const field of ["status_name", "statusName"]) {
    const receipt = { status: 7, [field]: "FINALIZED", ...execution };
    assert.equal(transactionStatus(receipt), "FINALIZED");
    assert.doesNotThrow(() => assertSuccessfulExecution(receipt));
  }
});

test("never interprets a numeric or intermediate status as finality", () => {
  assert.equal(transactionStatus({ status: 7 }), "");
  assert.throws(() => assertSuccessfulExecution({ status: 7, ...execution }), /not finalized/);
  assert.throws(() => assertSuccessfulExecution({ status_name: "ACCEPTED", ...execution }), /not finalized/);
});

test("rejects finalized but rolled-back contract execution", () => {
  const receipt = {
    status_name: "FINALIZED",
    consensus_data: { leader_receipt: [{ execution_result: "ERROR", result: { status: "rollback", payload: "Rejected" } }] },
  };
  assert.throws(() => assertSuccessfulExecution(receipt), /Rejected/);
});

test("recovers deposit hashes from wallet and contract activity without a supplied hash", () => {
  const wallet = "0x992F66909d0d843FAF079c82E89F4078e3A86d14";
  const contract = "0x9789420955ca6bceCdc408068Be987471DF77812";
  const hash = "0x46319501f063e8098c7fc413fe8ad9a479eb7f2c3d16da8c6a6828cca60bd366";
  const deposit = { hash, from_address: wallet.toLowerCase(), to_address: contract,
    value: "4000000000000000", created_at: "2026-10-05T07:30:00Z" };
  const history = [
    { ...deposit, value: 0 },
    { ...deposit, from_address: contract },
    { ...deposit, to_address: wallet },
    deposit,
    { ...deposit, from_address: wallet },
  ];
  assert.deepEqual(depositHistoryCandidates(history, wallet, contract), [{ hash, createdAt: deposit.created_at }]);
  assert.throws(() => depositHistoryCandidates({}, wallet, contract), /invalid wallet activity/);
});
