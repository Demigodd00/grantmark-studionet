# GRANTMARK — Project Explorer submission draft

This is the prepared submission copy. Use the [GenLayer Portal](https://portal.genlayer.foundation/) from the account that owns the project. The date should match the actual day of submission. Before submitting, verify that the live sample has a finalized GenLayer decision and withdrawal proof, or explicitly present it as an in-progress review. The current [acceptance journal](../deployments/grantmark_acceptance.json) is the source of truth.

## Project identity

**Project name:** GRANTMARK  
**Primary tag:** AI & Agents, if offered  
**Additional tags:** Grants, Source Verification, or Verifiable Inference, choosing from the portal's available taxonomy  
**Contribution date:** Enter the actual submission date  
**Logo:** [GRANTMARK logo](grantmark-logo.png) (1024 × 1024 PNG, under 2 MB)

## One-liner

> Grant tranches released or refunded by GenLayer validators against locked milestones and public evidence.

## Description

> GRANTMARK is a StudioNet app for evidence-backed grant milestones. A sponsor locks a test-GEN tranche, named beneficiary, measurable rubric and deadlines in an Intelligent Contract. The beneficiary submits a report and public HTTPS evidence; the sponsor may add one objection and counter-source. Once review closes, GenLayer validators independently fetch the bounded sources and decide MET, NOT_MET or INCONCLUSIVE. The contract credits the beneficiary only for MET and refunds the sponsor otherwise. Missed submissions and adjudication timeouts also have explicit refund paths. Parties withdraw their own credits. The frontend reads finalized contract state directly, with no central verdict backend or administrator override. The public sample uses synthetic, project-controlled evidence.

## How to review

1. Open the [live GRANTMARK docket](https://grantmark-web.vercel.app) without a wallet.
2. Open [the sample grant](https://grantmark-web.vercel.app/?grant=grm-1) and inspect its locked rubric, deadline, terms digest, beneficiary report, and public evidence link. The evidence is explicitly synthetic.
3. Follow the [deployed contract](https://explorer-studio.genlayer.com/address/0x9789420955ca6bceCdc408068Be987471DF77812), [contract source](../contracts/grantmark.py), [deployment manifest](../deployments/grantmark_studionet.json), and [acceptance journal](../deployments/grantmark_acceptance.json). The journal links finalized funding, creation and submission transactions.
4. Read the [reviewer guide](GRANTMARK_REVIEW.md) for settlement rules, test coverage, and the exact status of live adjudication and withdrawal.

## Expected verification outcome

> The app shows grm-1 with a locked 0.004 test-GEN tranche, rubric, beneficiary evidence, and review deadline. The deployment source and configuration are verified, and the acceptance journal proves finalized deposit, creation and submission. Direct tests verify MET, NOT_MET, INCONCLUSIVE, deadline refunds, withdrawal credit and validator rejection of edited evidence. Live verdict and withdrawal proof must be added after the review deadline; do not claim them before they exist.

## Project links and evidence

- **Website:** [GRANTMARK live app](https://grantmark-web.vercel.app)
- **GitHub:** [GRANTMARK standalone repository](https://github.com/Demigodd00/grantmark-studionet)
- **Contract:** [StudioNet explorer](https://explorer-studio.genlayer.com/address/0x9789420955ca6bceCdc408068Be987471DF77812)
- **Sample:** [grm-1](https://grantmark-web.vercel.app/?grant=grm-1)
- **Reviewer guide:** [GRANTMARK_REVIEW.md](GRANTMARK_REVIEW.md)
- **Acceptance evidence:** [grantmark_acceptance.json](../deployments/grantmark_acceptance.json)
- **Deployment evidence:** [grantmark_studionet.json](../deployments/grantmark_studionet.json)
- **CI checks:** [GitHub Actions](https://github.com/Demigodd00/grantmark-studionet/actions)

The repository is dedicated to GRANTMARK. It contains the contract, web app, tests, deployment scripts and records, and reviewer material. It does not include other apps or wallet secrets.
