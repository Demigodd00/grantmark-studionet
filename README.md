# GRANTMARK

GRANTMARK is a standalone GenLayer StudioNet app for evidence-backed grant milestones. A sponsor locks one test-GEN tranche against a fixed rubric and deadline. The beneficiary submits public evidence. After review, GenLayer validators independently fetch the declared sources, decide `MET`, `NOT_MET`, or `INCONCLUSIVE`, and the contract credits the beneficiary or sponsor accordingly. Anyone can trigger resolution. There is no administrator verdict override.

**Live app:** [grantmark-web.vercel.app](https://grantmark-web.vercel.app) · **Sample grant:** [grm-1](https://grantmark-web.vercel.app/?grant=grm-1) · **StudioNet contract:** [0x978942…77812](https://explorer-studio.genlayer.com/address/0x9789420955ca6bceCdc408068Be987471DF77812) · **Reviewer guide:** [GRANTMARK_REVIEW.md](docs/GRANTMARK_REVIEW.md) · **Submission draft:** [GRANTMARK_SUBMISSION.md](docs/GRANTMARK_SUBMISSION.md)

## What is in this repository

- [`contracts/grantmark.py`](contracts/grantmark.py): pinned-runner GenLayer intelligent contract, on-chain evidence record, consensus decision, and pull-payment accounting.
- [`apps/grantmark-web`](apps/grantmark-web): wallet-enabled Next.js app reading finalized StudioNet state directly.
- [`tests/direct/test_grantmark.py`](tests/direct/test_grantmark.py): escrow, deadline, authorization, decision, and independent-source checks.
- [`scripts/deploy_grantmark.py`](scripts/deploy_grantmark.py): deployment preflight, StudioNet broadcast, source verification, and release manifest.
- [`docs/architecture.md`](docs/architecture.md): rules, boundaries, and limitations.
- [`deployments`](deployments): verifiable deployment and acceptance records.
- [`scripts/grantmark_acceptance.py`](scripts/grantmark_acceptance.py): resume-safe synthetic StudioNet funding, grant, and evidence run. Test wallet keys stay outside this repository.
- [`scripts/check_grantmark_release.py`](scripts/check_grantmark_release.py): read-only verifier for deployed source, finalized sample transactions, cited evidence, settlement, and exact native withdrawal.
- [`scripts/finish_grantmark_acceptance.py`](scripts/finish_grantmark_acceptance.py): after the real review deadline, request adjudication, withdraw the credited test GEN, and record the native transfer. It never overrides time.

## Grant lifecycle

1. The sponsor deposits test GEN into recoverable contract credit, then creates a grant with one beneficiary, tranche, milestone, measurable rubric, and two windows.
2. The beneficiary submits a report and one or two public HTTPS sources before the submission deadline. If no submission arrives, anyone can refund the tranche to the sponsor.
3. The sponsor may add one objection and one public counter-source before the review deadline. The sponsor cannot edit the rubric or decide the result.
4. Once review closes, anyone invokes `resolve`. Validators independently fetch the bounded sources. `MET` credits the beneficiary; `NOT_MET` and `INCONCLUSIVE` credit the sponsor. If adjudication has not completed within seven days, anyone can invoke the timeout refund.
5. Recipients withdraw their contract credit themselves.

The web sources may change before adjudication. The contract stores the pages reviewed, digests, and citations. The current app supports one milestone per grant and public evidence only. It uses StudioNet test GEN, not funds of real-world value.

## Develop and verify

Requires Python 3.12, Node 22+, pnpm 11, and the versions in `requirements-deploy.txt`.

```sh
python -m pip install -r requirements-deploy.txt
python scripts/prepare_gltest_runner.py
genvm-lint check contracts/grantmark.py
pytest -q tests/direct/test_grantmark.py
cd apps/grantmark-web
pnpm install --frozen-lockfile
pnpm test
pnpm typecheck
pnpm build
pnpm audit --prod --audit-level high
```

Create `apps/grantmark-web/.env.local` with `NEXT_PUBLIC_GRANTMARK_ADDRESS=<deployed address>` to enable live reads and writes. `python scripts/deploy_grantmark.py` runs preflight without broadcasting; `--deploy --ephemeral-studionet-deployer` deploys with a disposable test-network signer and writes the address to `.env.local`. Use `--resume-transaction <hash>` after an interrupted deployment confirmation, without broadcasting a second time.

The repository is dedicated to GRANTMARK and contains no other GenLayer applications.

The [synthetic sample grant](https://grantmark-web.vercel.app/?grant=grm-1) has a finalized `MET` decision and a verified 0.004 StudioNet test-GEN withdrawal to its beneficiary. The [acceptance journal](deployments/grantmark_acceptance.json) records the adjudication, withdrawal, and native child-transfer hashes. This project-controlled evidence demonstrates the app's adjudication path; it does not prove a real delivery. Run `python scripts/check_grantmark_release.py` to check the current public release without any wallet key.
