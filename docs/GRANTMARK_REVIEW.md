# GRANTMARK reviewer guide

GRANTMARK is a standalone GenLayer StudioNet grant-milestone app. It uses no central verdict server. [The public app](https://grantmark-web.vercel.app) reads finalized contract state from StudioNet and sends wallet writes to the [deployed contract](https://explorer-studio.genlayer.com/address/0x9789420955ca6bceCdc408068Be987471DF77812). The [project logo](grantmark-logo.png) and [submission draft](GRANTMARK_SUBMISSION.md) are also included.

## Inspect the live sample

1. Open [the synthetic kit-delivery grant](https://grantmark-web.vercel.app/?grant=grm-1). No wallet is required to inspect it. Review the locked milestone, measurable rubric, tranche, two deadlines, beneficiary report, public evidence link, and terms digest.
2. Check the [deployment manifest](../deployments/grantmark_studionet.json), which records a finalized deployment transaction, pinned runner, source digest, and verified contract configuration.
3. Check the [acceptance journal](../deployments/grantmark_acceptance.json), which records finalized deposit, grant-creation, and evidence-submission transactions. The 0.004 test-GEN tranche is locked. Run the [read-only verifier](../scripts/check_grantmark_release.py) to confirm the deployed source, transactions, state, and public fixture independently. The journal explicitly states what has not yet been verified on the hosted network.
4. Inspect the [contract source](../contracts/grantmark.py) and [financial and validator tests](../tests/direct/test_grantmark.py). Tests cover both settlement recipients, inconclusive refunds, deadline refunds, single-use authorization, withdrawal credit, and validator rejection of edited evidence.

The public register in the sample is synthetic and controlled by this project. It does not prove a real delivery. Live adjudication can start only after the on-chain review deadline; the sample was still in `SUBMITTED` state when the acceptance journal was written. Do not describe a live `MET` decision or completed withdrawal until the contract and journal show it.

The sample review deadline is **5 October 2026, 09:30:17 UTC**. After it passes, `python scripts/finish_grantmark_acceptance.py` can submit resolution, withdraw the winning party's test GEN, and extend the journal with the exact native child transfer. It uses the original private acceptance wallets stored outside this repository and does not simulate or advance network time.

## Settlement semantics

`MET` credits the beneficiary. `NOT_MET` and `INCONCLUSIVE` credit the sponsor. No submission by its deadline or no adjudication within seven days after review also refunds the sponsor. Recipients call `withdraw_credit` to transfer credited GEN. The sponsor may lodge one objection but cannot change the terms or decide the result. All funds are StudioNet test GEN.

The source is bounded to at most two beneficiary URLs and one sponsor URL, 48 KB per response and 6,000 extracted characters per page. Validators fetch the URLs independently and compare substantive outcomes and source snapshots. Web evidence may change or disappear between submission and adjudication; the decision records source digests, excerpts, and citations.
