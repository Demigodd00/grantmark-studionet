import assert from "node:assert/strict";
import { test } from "node:test";
import { assertSuccessfulExecution, transactionStatus } from "../src/lib/grantmark.ts";

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
