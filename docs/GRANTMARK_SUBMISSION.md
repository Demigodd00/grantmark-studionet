# GRANTMARK — Project Explorer submission draft

This is the prepared submission copy. Use the [GenLayer Portal](https://portal.genlayer.foundation/) from the account that owns the project, and enter the actual day of submission. The live sample now has a finalized GenLayer decision and exact withdrawal proof in the [acceptance journal](https://github.com/Demigodd00/grantmark-studionet/blob/main/deployments/grantmark_acceptance.json).

## Project identity

**Project name:** GRANTMARK  
**Primary tag:** AI & Agents, if offered  
**Additional tags:** Grants, Source Verification, or Verifiable Inference, choosing from the portal's available taxonomy  
**Contribution date:** Enter the actual submission date  
**Logo:** [GRANTMARK logo](https://github.com/Demigodd00/grantmark-studionet/blob/main/docs/grantmark-logo.png) (1024 × 1024 PNG, under 2 MB)

## One-liner

> Grant tranches released or refunded by GenLayer validators against locked milestones and public evidence.

## Description

> GRANTMARK is a StudioNet app for evidence-backed grant milestones. A sponsor locks a test-GEN tranche, named beneficiary, measurable rubric and deadlines in an Intelligent Contract. The beneficiary submits a report and public HTTPS evidence; the sponsor may add one objection and counter-source. Once review closes, GenLayer validators independently fetch the bounded sources and decide MET, NOT_MET or INCONCLUSIVE. The contract credits the beneficiary only for MET and refunds the sponsor otherwise. Missed submissions and adjudication timeouts also have explicit refund paths. Parties withdraw their own credits. The frontend reads finalized contract state and recovers deposit status by wallet, without a supplied hash. There is no central verdict backend or administrator override. The public sample uses synthetic, project-controlled evidence.

## How to review

1. Open the [live GRANTMARK docket](https://grantmark-web.vercel.app) without a wallet.
2. Open [the sample grant](https://grantmark-web.vercel.app/?grant=grm-1) and inspect its locked rubric, deadline, terms digest, beneficiary report, synthetic evidence, `MET` decision, and citations.
3. Follow the [deployed contract](https://explorer-studio.genlayer.com/address/0x9789420955ca6bceCdc408068Be987471DF77812), [contract source](https://github.com/Demigodd00/grantmark-studionet/blob/main/contracts/grantmark.py), [deployment manifest](https://github.com/Demigodd00/grantmark-studionet/blob/main/deployments/grantmark_studionet.json), and [acceptance journal](https://github.com/Demigodd00/grantmark-studionet/blob/main/deployments/grantmark_acceptance.json). The journal links finalized funding, creation, submission, adjudication, and withdrawal transactions, plus the exact native child transfer.
4. Read the [reviewer guide](https://github.com/Demigodd00/grantmark-studionet/blob/main/docs/GRANTMARK_REVIEW.md) for settlement rules, test coverage, and the distinction between this synthetic demonstration and a real delivery.

## Expected verification outcome

> The app shows grm-1 as `MET` after the real review deadline. The finalized GenLayer transaction credited its beneficiary with 0.004 StudioNet test GEN; the beneficiary withdrew the exact amount through one finalized native child transfer. The acceptance journal and read-only verifier prove the transaction chain, recipient, amount, cited evidence snapshot, and cleared credit. Direct tests cover the other outcomes and refund paths. The public evidence is a disclosed, project-controlled synthetic fixture, not proof of a real grant distribution.

## Project links and evidence

- **Website:** [GRANTMARK live app](https://grantmark-web.vercel.app)
- **GitHub:** [GRANTMARK standalone repository](https://github.com/Demigodd00/grantmark-studionet)
- **Contract:** [StudioNet explorer](https://explorer-studio.genlayer.com/address/0x9789420955ca6bceCdc408068Be987471DF77812)
- **Sample:** [grm-1](https://grantmark-web.vercel.app/?grant=grm-1)
- **Adjudication:** [finalized GenLayer decision](https://explorer-studio.genlayer.com/tx/0x63ca3839ff8ddb2cb63156cc7f24342bee46dea6e6ed74dac74416fe8dbac57f)
- **Withdrawal:** [finalized contract write](https://explorer-studio.genlayer.com/tx/0xe55875af6dce4fc5947e86a1be69b0440bcaef00bf213eb7526b5977d60d71ea)
- **Payout:** [native child transfer to beneficiary](https://explorer-studio.genlayer.com/tx/0x7a13225c32a2da7fe5e18f5822031ba2ae83f85cfc7c061844cf32723db130d6)
- **Reviewer guide:** [GRANTMARK_REVIEW.md](https://github.com/Demigodd00/grantmark-studionet/blob/main/docs/GRANTMARK_REVIEW.md)
- **Acceptance evidence:** [grantmark_acceptance.json](https://github.com/Demigodd00/grantmark-studionet/blob/main/deployments/grantmark_acceptance.json)
- **Deployment evidence:** [grantmark_studionet.json](https://github.com/Demigodd00/grantmark-studionet/blob/main/deployments/grantmark_studionet.json)
- **CI checks:** [GitHub Actions](https://github.com/Demigodd00/grantmark-studionet/actions)
- **Read-only release verifier:** [check_grantmark_release.py](https://github.com/Demigodd00/grantmark-studionet/blob/main/scripts/check_grantmark_release.py)

The repository is dedicated to GRANTMARK. It contains the contract, web app, tests, deployment scripts and records, and reviewer material. It does not include other apps or wallet secrets.
