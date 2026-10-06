# GRANTMARK reviewer guide

GRANTMARK is a standalone GenLayer StudioNet grant-milestone app. It uses no central verdict server. [The public app](https://grantmark-web.vercel.app) reads finalized contract state from StudioNet and sends wallet writes to the [deployed contract](https://explorer-studio.genlayer.com/address/0x9789420955ca6bceCdc408068Be987471DF77812). The [project logo](grantmark-logo.png) and [submission draft](GRANTMARK_SUBMISSION.md) are also included.

Connected wallets can see recent deposits discovered from StudioNet wallet activity, without supplying a transaction hash. The app distinguishes a finalized successful credit from a pending, failed, or unknown transaction and retains pending write hashes across reloads.

## Inspect the live sample

1. Open [the synthetic kit-delivery grant](https://grantmark-web.vercel.app/?grant=grm-1). No wallet is required to inspect it. Review the locked milestone, measurable rubric, tranche, two deadlines, beneficiary report, public evidence link, and terms digest.
2. Check the [deployment manifest](../deployments/grantmark_studionet.json), which records a finalized deployment transaction, pinned runner, source digest, and verified contract configuration.
3. Check the [acceptance journal](../deployments/grantmark_acceptance.json), which records finalized deposit, grant-creation, evidence-submission, adjudication, and withdrawal transactions. Run the [read-only verifier](../scripts/check_grantmark_release.py) to confirm the deployed source, finalized state, evidence citations, settlement recipient, cleared credit, and exact native transfer independently.
4. Inspect the [contract source](../contracts/grantmark.py) and [financial and validator tests](../tests/direct/test_grantmark.py). Tests cover both settlement recipients, inconclusive refunds, deadline refunds, single-use authorization, withdrawal credit, and validator rejection of edited evidence.

The sample finalized as `MET` on 6 October 2026. The contract credited the beneficiary with 0.004 StudioNet test GEN, and a finalized withdrawal transferred exactly that amount to the beneficiary wallet. The [adjudication transaction](https://explorer-studio.genlayer.com/tx/0x63ca3839ff8ddb2cb63156cc7f24342bee46dea6e6ed74dac74416fe8dbac57f), [withdrawal transaction](https://explorer-studio.genlayer.com/tx/0xe55875af6dce4fc5947e86a1be69b0440bcaef00bf213eb7526b5977d60d71ea), and [native child transfer](https://explorer-studio.genlayer.com/tx/0x7a13225c32a2da7fe5e18f5822031ba2ae83f85cfc7c061844cf32723db130d6) are recorded in the journal.

The public register is synthetic and controlled by this project. The `MET` verdict demonstrates GenLayer adjudicating the declared source and contract settlement; it does **not** prove a real delivery. The on-chain review deadline was **5 October 2026, 09:30:17 UTC**. Resolution was submitted after that deadline without simulating or advancing network time. The acceptance wallets remain outside this repository.

## Settlement semantics

`MET` credits the beneficiary. `NOT_MET` and `INCONCLUSIVE` credit the sponsor. No submission by its deadline or no adjudication within seven days after review also refunds the sponsor. Recipients call `withdraw_credit` to transfer credited GEN. The sponsor may lodge one objection but cannot change the terms or decide the result. All funds are StudioNet test GEN.

The source is bounded to at most two beneficiary URLs and one sponsor URL, 48 KB per response and 6,000 extracted characters per page. Validators fetch the URLs independently and compare substantive outcomes and source snapshots. Web evidence may change or disappear between submission and adjudication; the decision records source digests, excerpts, and citations.
