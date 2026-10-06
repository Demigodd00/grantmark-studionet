"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  CONTRACT_ADDRESS, CONTRACT_READY, EXPLORER_URL, connectWallet, formatGen, getCredit,
  getGrant, getPendingTransaction, getStats, getWalletDeposits, listGrants, parseGen, reconcilePendingTransaction,
  shortenAddress, writeContract,
  type GrantRecord, type GrantSummary, type ProtocolStats, type Provider, type WalletDeposit, type WalletSession,
} from "@/lib/grantmark";

declare global { interface Window { ethereum?: Provider } }

const REPO = "https://github.com/Demigodd00/grantmark-studionet";
const DAY = 86400;
const initialDraft = {
  title: "", milestone: "", rubric: "", beneficiary: "", tranche: "0.01",
  submissionDays: "7", reviewDays: "2",
};

function date(epoch: string | number): string {
  const time = Number(epoch);
  return Number.isFinite(time) && time > 0
    ? new Date(time * 1000).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })
    : "—";
}

function label(outcome: string, status: string): string {
  if (outcome === "NO_SUBMISSION" || outcome === "TIMEOUT_REFUND") return "REFUNDED";
  if (outcome) return outcome.replaceAll("_", " ");
  return status === "SUBMITTED" ? "IN REVIEW" : status;
}

function stateClass(outcome: string, status: string): string {
  if (outcome === "MET") return "good";
  if (outcome === "NOT_MET" || outcome === "INCONCLUSIVE" || outcome.includes("REFUND") || outcome === "NO_SUBMISSION") return "closed";
  return status === "SUBMITTED" ? "review" : "open";
}

export default function GrantmarkApp() {
  const [session, setSession] = useState<WalletSession | null>(null);
  const [grants, setGrants] = useState<GrantSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<ProtocolStats | null>(null);
  const [selected, setSelected] = useState<GrantRecord | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [credit, setCredit] = useState("0");
  const [deposit, setDeposit] = useState("0.01");
  const [draft, setDraft] = useState(initialDraft);
  const [report, setReport] = useState("");
  const [evidenceUrls, setEvidenceUrls] = useState("");
  const [objection, setObjection] = useState("");
  const [objectionUrl, setObjectionUrl] = useState("");
  const [notice, setNotice] = useState("");
  const [noticeHash, setNoticeHash] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [panel, setPanel] = useState<"explore" | "create">("explore");
  const [pending, setPending] = useState<string | null>(null);
  const [walletDeposits, setWalletDeposits] = useState<WalletDeposit[]>([]);
  const [historyError, setHistoryError] = useState("");
  const refreshSequence = useRef(0);

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("grant");
    if (id && /^grm-\d+$/.test(id)) setSelectedId(id);
  }, []);

  const refresh = useCallback(async (id = selectedId, wallet = session) => {
    const sequence = ++refreshSequence.current;
    if (!CONTRACT_READY) { setLoading(false); return; }
    setLoadError(false);
    try {
      const [page, nextStats, detail, nextCredit] = await Promise.all([
        listGrants(0), getStats(), id ? getGrant(id) : Promise.resolve(null),
        wallet ? getCredit(wallet.address) : Promise.resolve("0"),
      ]);
      if (sequence !== refreshSequence.current) return;
      setGrants(page.items); setTotal(page.total); setStats(nextStats); setSelected(detail); setCredit(nextCredit);
      if (wallet) {
        setPending(getPendingTransaction(wallet.address)?.hash ?? null);
        void getWalletDeposits(wallet.address).then((items) => {
          if (sequence !== refreshSequence.current) return;
          setWalletDeposits(items); setHistoryError("");
        }).catch(() => {
          if (sequence === refreshSequence.current) setHistoryError("Wallet history is temporarily unavailable. Refresh to try again.");
        });
      } else { setWalletDeposits([]); setHistoryError(""); }
    } catch {
      if (sequence !== refreshSequence.current) return;
      setGrants([]); setTotal(0); setStats(null); setSelected(null);
      setLoadError(true);
    } finally {
      if (sequence === refreshSequence.current) setLoading(false);
    }
  }, [selectedId, session]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function connect() {
    if (!window.ethereum) { setNotice("Install an EVM wallet such as MetaMask to use StudioNet."); return; }
    setBusy(true);
    try {
      const wallet = await connectWallet(window.ethereum);
      setSession(wallet); setNotice("");
      await refresh(selectedId, wallet);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not connect wallet."); }
    finally { setBusy(false); }
  }

  async function send(method: string, args: unknown[], value = 0n) {
    if (!session) { setNotice("Connect a wallet first."); return; }
    setBusy(true); setNotice(""); setNoticeHash("");
    try {
      const hash = await writeContract(session, method, args, value, (submitted) => {
        setNoticeHash(submitted); setPending(submitted);
        setNotice("Transaction submitted. Waiting for StudioNet finality; keep this page open or return to check it.");
      });
      setNoticeHash(hash); setPending(null);
      setNotice("Transaction finalized successfully. Finalized contract state is refreshing.");
      await refresh(selectedId, session);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Transaction failed.");
      try { setPending(getPendingTransaction(session.address)?.hash ?? null); } catch { /* Preserve the visible error. */ }
    } finally { setBusy(false); }
  }

  async function recover() {
    if (!session) return;
    setBusy(true);
    try {
      const result = await reconcilePendingTransaction(session);
      setNotice(result.message); setNoticeHash(result.hash ?? "");
      setPending(result.done ? null : result.hash ?? null);
      if (result.done) await refresh(selectedId, session);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not check transaction."); }
    finally { setBusy(false); }
  }

  function openGrant(id: string) {
    setSelectedId(id); setSelected(null); setPanel("explore");
    window.history.replaceState(null, "", `?grant=${encodeURIComponent(id)}`);
    if (id === selectedId) void refresh(id, session);
  }

  function create() {
    try {
      const tranche = parseGen(draft.tranche);
      const submissionSecs = Math.round(Number(draft.submissionDays) * DAY);
      const reviewSecs = Math.round(Number(draft.reviewDays) * DAY);
      if (!Number.isSafeInteger(submissionSecs) || !Number.isSafeInteger(reviewSecs)) throw new Error("Enter valid deadline lengths.");
      void send("create_grant", [draft.title, draft.milestone, draft.rubric, draft.beneficiary, submissionSecs, reviewSecs, tranche]);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Invalid grant details."); }
  }

  function submit() {
    if (!selected) return;
    const urls = evidenceUrls.split(/\r?\n/).map((url) => url.trim()).filter(Boolean);
    void send("submit_evidence", [selected.id, report, JSON.stringify(urls)]);
  }

  const now = Math.floor(Date.now() / 1000);
  const isSponsor = !!selected && session?.address.toLowerCase() === selected.sponsor.toLowerCase();
  const isBeneficiary = !!selected && session?.address.toLowerCase() === selected.beneficiary.toLowerCase();

  return <div className="site-shell">
    <header className="site-header">
      <a className="brand" href="#top" aria-label="GRANTMARK home"><span className="brand-icon">G<span>.</span></span><span>GRANTMARK</span></a>
      <nav><a href="#how">How it works</a><a href="#grants">Grant docket</a><a href={REPO} target="_blank" rel="noreferrer">Source ↗</a></nav>
      <button className="wallet-button" onClick={connect} disabled={busy}>{session ? shortenAddress(session.address) : "Connect wallet"}<span className="wallet-dot" /></button>
    </header>

    <main id="top">
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span className="live-dot" /> BUILT ON GENLAYER STUDIONET <span className="eyebrow-line" /> GRANTS, WITH PROOF</div>
          <h1>Make every<br /><em>milestone</em> count.</h1>
          <p>Lock a grant to a clear result. Let the beneficiary show the work. GenLayer validators inspect the public evidence and settle the tranche by the rules you set up front.</p>
          <div className="hero-actions"><button className="primary" onClick={() => { setPanel("create"); document.getElementById("workspace")?.scrollIntoView({ behavior: "smooth" }); }}>Create a grant <span>↗</span></button><a className="secondary" href="#grants">Explore grants <span>↘</span></a></div>
          <div className="hero-note"><span className="hero-note-mark">✳</span> PUBLIC EVIDENCE <span>·</span> INDEPENDENT REVIEW <span>·</span> ON-CHAIN SETTLEMENT</div>
        </div>
        <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit orbit-three" /><div className="art-card"><span className="art-kicker">MILESTONE / 001</span><span className="art-check">✓</span><strong>Work verified.<br />Funds released.</strong><span className="art-rule" /><span className="art-footer">EVIDENCE → CONSENSUS → SETTLEMENT</span></div><span className="art-cross cross-a">✳</span><span className="art-cross cross-b">+</span></div>
      </section>

      <section className="metric-strip" aria-label="Protocol statistics">
        <div><strong>{stats?.total_created ?? "—"}</strong><span>GRANTS CREATED</span></div>
        <div><strong>{stats ? formatGen(stats.total_locked_atto) : "—"}</strong><span>GEN CURRENTLY LOCKED</span></div>
        <div><strong>{stats?.total_met ?? "—"}</strong><span>MILESTONES MET</span></div>
        <div><strong>01 / 01</strong><span>FIXED RUBRIC PER GRANT</span></div>
      </section>

      <section className="how-section" id="how"><div className="section-head"><span className="section-index">01 / THE PROCESS</span><h2>Clarity before<br /><i>capital moves.</i></h2><p>Each step leaves a public trail. The sponsor sets the terms, the beneficiary supplies evidence, and the contract settles from GenLayer’s finalized decision.</p></div><div className="step-grid"><article><span>01 — DEFINE</span><div className="step-icon">◇</div><h3>Lock the rules</h3><p>Set the milestone, a measurable rubric, beneficiary, deadlines, and GEN tranche. Terms cannot change after creation.</p></article><article><span>02 — PROVE</span><div className="step-icon">↗</div><h3>Submit evidence</h3><p>The beneficiary links public records. The sponsor can add one bounded objection and counter-source during review.</p></article><article><span>03 — SETTLE</span><div className="step-icon">✳</div><h3>Resolve on-chain</h3><p>Validators read the declared sources independently. MET releases to the beneficiary; all other outcomes refund the sponsor.</p></article></div></section>

      <section className="workspace" id="workspace"><div className="workspace-head"><div><span className="section-index">02 / YOUR WORKSPACE</span><h2>Put a grant<br /><i>on the record.</i></h2></div><p>StudioNet uses test GEN. Deposit to recoverable credit first, then lock exactly one tranche in a grant. Unused credit is always withdrawable.</p></div><div className="workspace-layout"><div className="workspace-main"><div className="tabs"><button className={panel === "explore" ? "active" : ""} onClick={() => setPanel("explore")}>Explore docket</button><button className={panel === "create" ? "active" : ""} onClick={() => setPanel("create")}>Create grant</button></div>{panel === "create" ? <div className="form-panel"><div className="form-intro"><span>NEW GRANT / STUDIO NET</span><p>Be specific. Validators apply exactly the rubric you lock here.</p></div><div className="field-grid"><label>Grant title<input value={draft.title} maxLength={96} placeholder="e.g. Community water audit" onChange={(e) => setDraft({ ...draft, title: e.target.value })} /></label><label>Beneficiary wallet<input value={draft.beneficiary} placeholder="0x…" onChange={(e) => setDraft({ ...draft, beneficiary: e.target.value })} /></label><label className="wide">Milestone<textarea value={draft.milestone} maxLength={1600} placeholder="What concrete result must be delivered?" onChange={(e) => setDraft({ ...draft, milestone: e.target.value })} /></label><label className="wide">Verification rubric<textarea value={draft.rubric} maxLength={1400} placeholder="State what counts as MET, NOT_MET, or INCONCLUSIVE." onChange={(e) => setDraft({ ...draft, rubric: e.target.value })} /></label><label>Tranche · GEN<input type="number" min="0.004" step="0.001" value={draft.tranche} onChange={(e) => setDraft({ ...draft, tranche: e.target.value })} /></label><label>Submission window · days<input type="number" min="0.042" max="90" step="0.1" value={draft.submissionDays} onChange={(e) => setDraft({ ...draft, submissionDays: e.target.value })} /></label><label>Review window · days<input type="number" min="0.042" max="14" step="0.1" value={draft.reviewDays} onChange={(e) => setDraft({ ...draft, reviewDays: e.target.value })} /></label></div><button className="primary form-submit" disabled={busy || !session || !CONTRACT_READY} onClick={create}>Lock grant terms <span>↗</span></button><p className="microcopy">Requires at least {draft.tranche || "0"} GEN of available contract credit.</p></div> : <div id="grants" className="docket"><div className="docket-toolbar"><span>LIVE GRANT DOCKET</span><span>{loadError ? "COUNT UNAVAILABLE" : `${total} RECORDS`} <button onClick={() => void refresh()} disabled={busy}>↻ REFRESH</button></span></div>{loading ? <div className="empty">Reading finalized StudioNet state…</div> : loadError ? <div className="empty" role="alert">StudioNet data could not be read. The grant count is unknown. <button onClick={() => void refresh()}>Retry read ↻</button></div> : !CONTRACT_READY ? <div className="empty">The StudioNet contract address is not configured yet.</div> : grants.length === 0 ? <div className="empty">No grants have been created yet. Start the first verifiable milestone.</div> : grants.map((grant) => <button className={`grant-row ${selectedId === grant.id ? "selected" : ""}`} key={grant.id} onClick={() => openGrant(grant.id)}><span className="grant-id">{grant.id}</span><span className="grant-row-main"><strong>{grant.title}</strong><small>{grant.milestone}</small></span><span className="grant-amount">{formatGen(grant.tranche_atto)} <small>GEN</small></span><span className={`status ${stateClass(grant.outcome, grant.status)}`}>{label(grant.outcome, grant.status)}</span><span className="row-arrow">↗</span></button>)}</div>}</div><aside className="workspace-side"><div className="balance-card"><span className="side-kicker">YOUR CONTRACT CREDIT</span><strong>{formatGen(credit)} <small>GEN</small></strong><p>Available to lock in a grant or withdraw. A deposit is credited only after finalized execution.</p><label>Deposit test GEN<input type="number" min="0.004" step="0.001" value={deposit} onChange={(e) => setDeposit(e.target.value)} /></label><button disabled={busy || !session || !CONTRACT_READY} onClick={() => { try { void send("deposit", [], parseGen(deposit)); } catch (error) { setNotice(error instanceof Error ? error.message : "Invalid amount."); } }}>Deposit ↗</button><button className="ghost-button" disabled={busy || !session || BigInt(credit || "0") === 0n} onClick={() => void send("withdraw_credit", [])}>Withdraw available credit ↗</button></div>{session && <div className="history-card"><span className="side-kicker">RECENT WALLET DEPOSITS</span>{historyError ? <p>{historyError}</p> : walletDeposits.length === 0 ? <p>No deposits found for this wallet.</p> : walletDeposits.map((item) => <div className="history-row" key={item.hash}><div><strong>{item.amountAtto ? formatGen(item.amountAtto) + " GEN" : "Amount unavailable"}</strong><small>{item.outcome === "credited" ? "FINALIZED / CREDITED" : item.outcome === "failed" ? "EXECUTION FAILED" : item.outcome === "pending" ? "PENDING FINALITY" : "STATUS UNKNOWN"}</small></div><a href={`https://explorer-studio.genlayer.com/tx/${item.hash}`} target="_blank" rel="noreferrer" title={item.hash}>VIEW</a></div>)}</div>}<div className="side-info"><span>PROTOCOL NOTE / 001</span><p>Grant funds move only after GenLayer reaches a final result. A missing submission or adjudication timeout returns the tranche to the sponsor.</p><a href={EXPLORER_URL} target="_blank" rel="noreferrer">VIEW CONTRACT ↗</a></div></aside></div>

        {pending && <div className="pending-card"><div><strong>Transaction still being checked</strong><p>Saved hash: <a href={`https://explorer-studio.genlayer.com/tx/${pending}`} target="_blank" rel="noreferrer">{shortenAddress(pending)} ↗</a>. Do not resend until the result is known.</p></div><button onClick={() => void recover()} disabled={busy}>Check outcome</button></div>}
        {notice && <div className="notice" role="status">{notice}{noticeHash && <a href={`https://explorer-studio.genlayer.com/tx/${noticeHash}`} target="_blank" rel="noreferrer">View transaction ↗</a>}</div>}
      </section>

      {selected && <section className="detail-section" id="grant-detail"><div className="detail-heading"><div><span className="section-index">03 / GRANT RECORD · {selected.id}</span><h2>{selected.title}</h2></div><span className={`status ${stateClass(selected.outcome, selected.status)}`}>{label(selected.outcome, selected.status)}</span></div>{selected.id === "grm-1" && selected.evidence_urls.includes("https://grantmark-web.vercel.app/evidence/demo-register.txt") && <p className="demo-disclosure" role="note"><strong>SYNTHETIC DEMO</strong> This register was created for testing. It does not prove that real school kits were delivered. The tranche uses StudioNet test GEN.</p>}<div className="detail-grid"><div className="detail-main"><div className="detail-block"><span>MILESTONE</span><p>{selected.milestone}</p></div><div className="detail-block"><span>LOCKED VERIFICATION RUBRIC</span><p>{selected.rubric}</p></div>{selected.report && <div className="detail-block"><span>BENEFICIARY REPORT</span><p>{selected.report}</p><div className="links">{selected.evidence_urls.map((url) => <a key={url} href={url} target="_blank" rel="noreferrer">Evidence source ↗</a>)}</div></div>}{selected.objection && <div className="detail-block"><span>SPONSOR OBJECTION</span><p>{selected.objection.argument}</p><a href={selected.objection.source_url} target="_blank" rel="noreferrer">Counter-evidence ↗</a></div>}{selected.outcome && <div className="detail-block result-block"><span>GENLAYER DECISION · {selected.outcome.replaceAll("_", " ")}</span><p>{selected.reason}</p>{selected.citations.map((citation, index) => <a key={`${citation.source_id}-${index}`} href={citation.url} target="_blank" rel="noreferrer">{citation.source_id}, line {citation.line}: {citation.excerpt} ↗</a>)}</div>}</div><div className="detail-aside"><div><span>SPONSOR</span><strong>{shortenAddress(selected.sponsor)}</strong></div><div><span>BENEFICIARY</span><strong>{shortenAddress(selected.beneficiary)}</strong></div><div><span>TRANCHE</span><strong>{formatGen(selected.tranche_atto)} GEN</strong></div><div><span>SUBMISSION DEADLINE</span><strong>{date(selected.submission_deadline)}</strong></div><div><span>REVIEW CLOSES</span><strong>{date(selected.review_deadline)}</strong></div><div><span>TERMS DIGEST</span><code title={selected.terms_digest}>{selected.terms_digest.slice(0, 18)}…</code></div></div></div>
        {selected.status === "OPEN" && isBeneficiary && now < selected.submission_deadline && <div className="action-panel"><span>BENEFICIARY ACTION / SUBMIT ONCE</span><h3>Show the work</h3><p>Supply one or two public HTTPS links, one per line. These are locked when you submit.</p><textarea placeholder="Describe what was delivered and when." value={report} onChange={(e) => setReport(e.target.value)} /><textarea placeholder="https://public-source.example/report" value={evidenceUrls} onChange={(e) => setEvidenceUrls(e.target.value)} /><button className="primary" disabled={busy || !!pending} onClick={submit}>Submit evidence ↗</button></div>}
        {selected.status === "SUBMITTED" && isSponsor && !selected.objection && now < selected.review_deadline && <div className="action-panel"><span>SPONSOR ACTION / OPTIONAL</span><h3>Challenge the evidence</h3><p>One objection and one public source may be added before review closes.</p><textarea placeholder="What material condition does the evidence fail?" value={objection} onChange={(e) => setObjection(e.target.value)} /><input placeholder="https://public-source.example/audit" value={objectionUrl} onChange={(e) => setObjectionUrl(e.target.value)} /><button className="primary" disabled={busy || !!pending} onClick={() => void send("object_to_evidence", [selected.id, objection, objectionUrl])}>Submit objection ↗</button></div>}
        {selected.status === "OPEN" && now >= selected.submission_deadline && <button className="primary resolution-button" disabled={busy || !session || !!pending} onClick={() => void send("expire_unsubmitted", [selected.id])}>Refund missed milestone ↗</button>}
        {selected.status === "SUBMITTED" && now >= selected.review_deadline && now < selected.review_deadline + 7 * DAY && <button className="primary resolution-button" disabled={busy || !session || !!pending} onClick={() => void send("resolve", [selected.id])}>Request GenLayer adjudication ↗</button>}
        {selected.status === "SUBMITTED" && now >= selected.review_deadline + 7 * DAY && <button className="primary resolution-button" disabled={busy || !session || !!pending} onClick={() => void send("expire_unresolved", [selected.id])}>Refund timed-out grant ↗</button>}
      </section>}
    </main>
    <footer><div className="footer-logo">G<span>.</span> <small>GRANTMARK</small></div><p>Evidence-backed grants, settled on GenLayer.</p><div><a href={REPO} target="_blank" rel="noreferrer">GITHUB ↗</a><a href={EXPLORER_URL} target="_blank" rel="noreferrer">STUDIONET ↗</a></div><span>© {new Date().getFullYear()} GRANTMARK</span></footer>
  </div>;
}
