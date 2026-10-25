import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowUpRight, Check, CircleAlert, Copy, RotateCw, ShieldCheck, X } from "lucide-react";
import { ApiError, apiUrl, validateRepository } from "./services/api";
import { enrichFindings } from "./feedback";
import { OpeningArtwork, RooftopArtwork } from "./components/RooftopArtwork";
import { WebSlingerScene } from "./components/WebSlingerScene";
import type { Finding, FindingFilter, ResultState, ValidationReport } from "./types";

type Scene = "intro" | "briefing" | "analysis";
const fade = { initial: { opacity: 0, y: 14 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -8 } };
const statusText = (value?: string | null) => value ? value.replaceAll("_", " ") : "not reported";
const findingRank = (severity?: string) => severity === "error" ? 0 : severity === "warning" ? 1 : severity === "info" ? 2 : 3;

function repositoryLabel(value: string): string {
  try {
    const parsed = new URL(value);
    const parts = parsed.pathname.split("/").filter(Boolean);
    if (parsed.hostname.toLowerCase() === "github.com" && parts.length >= 2) return `${parts[0]}/${parts[1]}`;
  } catch { /* Keep the caller's original identifier if it is not a URL. */ }
  return value;
}

export function resultState(data: ValidationReport): ResultState {
  if (data.validation_status === "failed") return "error";
  if (["failed", "collection_failed", "timed_out", "runner_error"].includes(data.test_status ?? "")) return "failure";
  if (data.findings?.some((finding) => finding.severity === "error")) return "failure";
  if (data.configuration_status === "issues_found" || data.findings?.some((finding) => finding.severity === "warning")) return "warning";
  if (data.readiness_assessment === "checks_passed") return "success";
  return "partial";
}

function stateLabel(state: ResultState): string {
  return ({ success: "CHECKS PASSED", failure: "TESTS NEED ATTENTION", warning: "CONFIGURATION NEEDS REVIEW", error: "INSPECTION INCOMPLETE", partial: "PARTIAL READOUT" })[state];
}

function Brand({ onHome }: { onHome: () => void }) {
  return <a className="wordmark" href="#top" aria-label="RepoCheck home" onClick={(event) => { event.preventDefault(); onHome(); }}><span className="brand-mark" aria-hidden="true"><Check size={22} /></span>Repo<span>Check</span></a>;
}

function CopyButton({ value, children, onCopied }: { value: string; children: React.ReactNode; onCopied: (label: string) => void }) {
  const [label, setLabel] = useState("");
  async function copy() {
    try { await navigator.clipboard.writeText(value); setLabel("Copied"); onCopied("Copied to clipboard."); }
    catch { setLabel("Unavailable"); onCopied("Clipboard unavailable. Select the text and copy it manually."); }
    window.setTimeout(() => setLabel(""), 2400);
  }
  return <button className="button button-outline copy-button" type="button" onClick={copy} aria-label={label ? `${children} ${label}` : undefined}><Copy size={14} />{label || children}</button>;
}

function FindingRow({ item, index, reduceMotion }: { item: Finding; index: number; reduceMotion: boolean }) {
  const [open, setOpen] = useState(false);
  const detailId = `finding-evidence-${index}`;
  return <motion.div className="finding-row" initial={reduceMotion ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22, delay: reduceMotion ? 0 : Math.min(index * 0.035, 0.21) }}>
    <button className="finding-summary" type="button" aria-expanded={open} aria-controls={detailId} onClick={() => setOpen((value) => !value)}><span className={`severity severity-${item.severity || "info"}`}><i />{item.severity || "info"}</span><span className="finding-heading"><strong>{item.title || "Finding"}</strong><small>{item.code || ""}</small></span><span className="finding-plus" aria-hidden="true">＋</span></button>
    <motion.div id={detailId} className="finding-detail" initial={false} animate={{ height: open ? "auto" : 0, opacity: open ? 1 : 0 }} transition={{ duration: reduceMotion ? 0 : 0.2, ease: [0.2, 0.78, 0.22, 1] }} aria-hidden={!open} inert={!open}>
      {item.message && <p><b>Finding</b>{item.message}</p>}
      <p><b>Evidence</b>{item.evidence || "No additional evidence was included in the API response."}</p>
      {item.why && <p><b>Why it matters</b>{item.why}</p>}
      {item.file && <p className="mono"><b>Path</b>{item.file}</p>}
      {item.recommendation && <p><b>Recommended action</b>{item.recommendation}</p>}
      <p><b>Confidence / limitation</b>{[item.category, item.confidence].filter(Boolean).join(" · ") || "Based on the API finding."}</p>
    </motion.div>
  </motion.div>;
}

function ConfigGroup({ title, files, statuses, absent }: { title: string; files?: string[]; statuses?: Record<string, string>; absent: string }) {
  return <section className="config-group"><h3>{title}</h3>{files?.length ? <ul>{files.map((file) => <li key={file}><code>{file}</code><span>{statusText(statuses?.[file] || "found")}</span></li>)}</ul> : <p className="empty-state">{absent}</p>}</section>;
}

export default function App() {
  const reduceMotion = useReducedMotion() ?? false;
  const [scene, setScene] = useState<Scene>("intro");
  const [url, setUrl] = useState("");
  const [activeUrl, setActiveUrl] = useState("");
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<FindingFilter>("all");
  const [copyMessage, setCopyMessage] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [currentActivity, setCurrentActivity] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const progressAbortRef = useRef<AbortController | null>(null);
  const requestPendingRef = useRef(false);
  const urlRef = useRef<HTMLInputElement>(null);
  const reportRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => () => { abortRef.current?.abort(); progressAbortRef.current?.abort(); }, []);
  useEffect(() => { if (scene === "analysis" && report) reportRef.current?.focus({ preventScroll: true }); }, [scene, report]);

  const findings = useMemo(() => report
    ? enrichFindings(report).map((finding, index) => ({ finding, index }))
      .sort((a, b) => findingRank(a.finding.severity) - findingRank(b.finding.severity) || a.index - b.index)
      .map(({ finding }) => finding)
    : [], [report]);
  const filtered = findings.filter((item) => filter === "all" || item.severity === filter);

  async function runAnalysis(repositoryUrl: string) {
    if (requestPendingRef.current) return;
    requestPendingRef.current = true;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const progressController = new AbortController();
    progressAbortRef.current?.abort();
    progressAbortRef.current = progressController;
    const runId = crypto.randomUUID();
    setActiveUrl(repositoryUrl); setError(""); setReport(null); setFilter("all"); setCurrentActivity("Waiting for the validation worker to start."); setRequesting(true); setScene("analysis");
    void pollValidationProgress(runId, progressController.signal);
    try { setReport(await validateRepository(repositoryUrl, controller.signal, runId)); }
    catch (reason) {
      if (controller.signal.aborted) return;
      setError(reason instanceof ApiError ? reason.message : reason instanceof Error ? reason.message : "The request could not be completed.");
    } finally {
      progressController.abort();
      if (!controller.signal.aborted) { requestPendingRef.current = false; setRequesting(false); setCurrentActivity(""); }
    }
  }

  async function pollValidationProgress(runId: string, signal: AbortSignal) {
    await new Promise((resolve) => window.setTimeout(resolve, 250));
    while (!signal.aborted) {
      try {
        const response = await fetch(apiUrl(`/repositories/progress/${runId}`), { signal, headers: { Accept: "application/json" } });
        if (response.ok) {
          const result: unknown = await response.json();
          if (result && typeof result === "object" && "stage" in result && typeof result.stage === "string") setCurrentActivity(result.stage);
        }
      } catch {
        if (signal.aborted) return;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 500));
    }
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (requestPendingRef.current) return;
    const trimmed = url.trim();
    try {
      const parsed = new URL(trimmed);
      if (parsed.protocol !== "https:" || parsed.hostname.toLowerCase() !== "github.com" || parsed.pathname.split("/").filter(Boolean).length < 2) throw new Error();
    } catch { setError("Enter a valid HTTPS GitHub repository URL, such as https://github.com/owner/repo."); return; }
    void runAnalysis(trimmed);
  }

  function newAnalysis() { abortRef.current?.abort(); progressAbortRef.current?.abort(); requestPendingRef.current = false; setRequesting(false); setCurrentActivity(""); setReport(null); setError(""); setScene("briefing"); }
  function summaryText(data: ValidationReport): string {
    const rows = [`RepoCheck report: ${data.repository || activeUrl}`, `Validation: ${statusText(data.validation_status)}`, `Tests: ${statusText(data.test_status)}`, `Readiness: ${statusText(data.readiness_assessment)}`, `Configuration: ${statusText(data.configuration_status)}`, `Detected test files (${data.test_file_count ?? "not reported"}): ${(data.test_files || []).join(", ") || "none reported"}`];
    (data.findings || []).forEach((item) => rows.push(`- [${item.severity || "info"}] ${item.title || item.code}: ${item.message || ""}${item.recommendation ? ` Next: ${item.recommendation}` : ""}`));
    return rows.join("\n");
  }

  return <main id="top" className="app-shell min-h-screen">
    <AnimatePresence mode="wait" initial={false}>
      {scene === "intro" && <motion.section key="intro" className="scene intro-scene" {...fade} transition={{ duration: reduceMotion ? 0 : 0.34 }} aria-labelledby="intro-title">
        <OpeningArtwork className="intro-art" /><div className="intro-vignette" aria-hidden="true" />
        <header className="intro-nav"><Brand onHome={() => setScene("intro")} /><span className="system-tag"><i />REPOSITORY INTELLIGENCE SYSTEM</span></header>
        <div className="intro-copy"><p className="eyebrow"><i />FIELD OPERATIONS / 01</p><h1 id="intro-title">EVERY REPOSITORY<br />HAS A <em>STORY.</em></h1><p>Let's find out if yours is ready for action.</p><button className="button button-primary button-large" onClick={() => setScene("briefing")}>GET STARTED <ArrowUpRight size={17} /></button></div>
        <button className="skip-intro" onClick={() => setScene("briefing")}>Skip intro ↓</button><p className="intro-caption">CITY GRID / LIVE FROM THE ROOFTOP <span>·</span> READ ONLY</p>
      </motion.section>}
      {scene === "briefing" && <motion.section key="briefing" className="scene briefing-scene" {...fade} transition={{ duration: reduceMotion ? 0 : 0.28 }} aria-labelledby="briefing-title">
        <header className="top-nav"><Brand onHome={() => setScene("intro")} /><div className="nav-meta"><i /> FIELD BRIEFING <span className="nav-divider" /><a href="/docs" target="_blank" rel="noreferrer">API REFERENCE ↗</a></div></header>
        <div className="briefing-layout"><div className="art-frame"><RooftopArtwork className="rooftop-art" /><div className="visual-stamp"><span>FIELD NOTE 01</span><span>READ ONLY</span></div><div className="scan-beam" aria-hidden="true" /></div>
          <div className="briefing-copy"><p className="eyebrow"><i />MISSION BRIEFING / 01</p><h1 id="briefing-title">Alright, recruit.<br /><em>Drop the coordinates.</em></h1><p className="deck">Point RepoCheck at a public GitHub repository. We’ll inspect its test files and setup, then show the evidence. Hosted analysis does not execute repository tests.</p>
            <form onSubmit={submit} noValidate><label htmlFor="repo-url">REPOSITORY COORDINATES</label><div className="url-control"><span aria-hidden="true">↗</span><input ref={urlRef} autoFocus id="repo-url" type="url" inputMode="url" autoComplete="url" placeholder="https://github.com/owner/repo" value={url} onChange={(event) => setUrl(event.target.value)} aria-describedby="url-hint form-error" /><button className="button button-primary" type="submit">START ANALYSIS <ArrowUpRight size={16} /></button></div><p id="url-hint" className="field-hint">Public GitHub repositories · HTTPS only</p>{error && <p id="form-error" className="form-error" role="alert">{error}</p>}</form>
            <div className="briefing-rails" aria-label="Analysis capabilities"><div><b>01</b><span><strong>Trace the tests</strong><small>Detect Python / pytest files; execution depends on service mode</small></span></div><div><b>02</b><span><strong>Read the setup</strong><small>Known configuration and workflow paths</small></span></div><div><b>03</b><span><strong>Return with evidence</strong><small>Findings grounded in actual checks</small></span></div></div>
            <p className="safety-note"><ShieldCheck size={15} /> Hosted inspection does not execute repository code · local mode uses restricted Docker</p><button className="text-button" type="button" onClick={() => setScene("intro")}>← Back to the opening scene</button>
          </div></div><p className="screen-code">REPOCHECK / FIELD OPERATIONS <span>02 — BRIEFING</span></p>
      </motion.section>}
      {scene === "analysis" && <motion.section key="analysis" className="scene analysis-scene" {...fade} transition={{ duration: reduceMotion ? 0 : 0.24 }} aria-labelledby={requesting || error ? "analysis-title" : "report-title"} aria-busy={requesting}>
        <header className="top-nav report-nav"><Brand onHome={() => { newAnalysis(); setScene("intro"); }} /><div className="nav-meta"><i /> REPOSITORY INTELLIGENCE <span className="nav-divider" /><code>{report?.repository || activeUrl}</code></div><button className="button button-quiet" type="button" onClick={newAnalysis}>NEW ANALYSIS <ArrowUpRight size={15} /></button></header>
        {requesting && <div className="loading-state" role="status" aria-live="polite">
          <div className="loading-art"><WebSlingerScene reducedMotion={reduceMotion} /></div>
          <div className="loading-copy"><p className="analysis-repository">ANALYZING <code>{repositoryLabel(activeUrl)}</code></p><p className="eyebrow"><i />ANALYSIS IN PROGRESS</p><h1 id="analysis-title">Reading the repository.<br /><em>Tracing what it can prove.</em></h1><p>RepoCheck is inspecting repository metadata, setup, and supported test files. Whether tests run depends on this service’s execution mode. This screen stays active until the API returns its report.</p><div className="indeterminate-bar" role="progressbar" aria-label="Analysis in progress"><i /></div><p className="loading-activity" aria-live="polite"><span>CURRENT ACTIVITY</span><strong>{currentActivity}</strong><small>Server-reported stage · no estimated percentage or test count</small></p><small className="loading-footnote">NO REPOSITORY CODE ON THIS PAGE</small></div>
        </div>}
        {!requesting && error && <div className="error-state" role="alert"><p className="eyebrow"><i className="red" />UPLINK INTERRUPTED</p><h1 id="analysis-title">We lost the trail.<br /><em>The repository remains unjudged.</em></h1><p>{error.includes("HTTP") || error.includes("could not") ? `No validation report was returned, so the repository remains unjudged. ${error}` : error}</p><div className="error-actions"><button className="button button-primary" onClick={() => void runAnalysis(activeUrl)}><RotateCw size={15} /> RETRY ANALYSIS</button><button className="button button-outline" onClick={newAnalysis}>EDIT REPOSITORY</button></div></div>}
        {!requesting && report && <Report report={report} findings={findings} filtered={filtered} filter={filter} setFilter={setFilter} onCopy={setCopyMessage} copyMessage={copyMessage} summaryText={summaryText(report)} reportRef={reportRef} reduceMotion={reduceMotion} newAnalysis={newAnalysis} />}
      </motion.section>}
    </AnimatePresence>
  </main>;
}

function Report({ report, findings, filtered, filter, setFilter, onCopy, copyMessage, summaryText: summary, reportRef, reduceMotion, newAnalysis }: {
  report: ValidationReport; findings: Finding[]; filtered: Finding[]; filter: FindingFilter; setFilter: (filter: FindingFilter) => void;
  onCopy: (message: string) => void; copyMessage: string; summaryText: string; reportRef: React.RefObject<HTMLHeadingElement | null>; reduceMotion: boolean; newAnalysis: () => void;
}) {
  const state = resultState(report);
  const logBlocks = [report.stdout && `STDOUT\n${report.stdout}`, report.stderr && `STDERR\n${report.stderr}`].filter(Boolean) as string[];
  const logs = logBlocks.join("\n\n") || (report.execution_mode === "inspection_only" ? "Repository tests were not executed in inspection-only mode; no test output exists." : "No test output was returned.");
  const configuration = report.configuration;
  const factRows: Array<[string, string | number | undefined | null]> = [
    ["Repository", report.repository], ["Default branch", report.default_branch],
    ["Language / runner", [report.language, report.framework].filter(Boolean).join(" / ") || undefined],
    ["Test files detected", Number.isFinite(report.test_file_count) ? report.test_file_count : undefined],
    ["Exit code", report.exit_code],
    ["Execution time", Number.isFinite(report.duration_seconds) ? `${report.duration_seconds?.toFixed(2)} s` : undefined],
  ];
  const configGroups = [
    configuration?.workflows && <ConfigGroup key="workflows" title="GitHub Actions" files={configuration.workflows.files} statuses={Object.fromEntries((configuration.workflows.checks || []).map((item) => [item.file, item.status || "found"]))} absent="No workflow files found under .github/workflows/." />,
    configuration?.python_test_configuration && <ConfigGroup key="pytest" title="Python test configuration" files={configuration.python_test_configuration.files} statuses={configuration.python_test_configuration.validity} absent="No recognized pytest configuration files reported." />,
    configuration?.dependency_manifests && <ConfigGroup key="dependencies" title="Dependency manifests" files={configuration.dependency_manifests.files} statuses={configuration.dependency_manifests.syntax_status} absent="No recognized dependency manifests reported." />,
  ].filter(Boolean);
  return <motion.section className="mission-report" data-state={state} aria-labelledby="report-title" initial={reduceMotion ? false : { opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.27 }}>
    <div className="report-heading"><div><p className="eyebrow">MISSION REPORT / {report.test_status === "not_run" ? "INSPECTION ONLY · TESTS NOT RUN" : stateLabel(state)}</p><h1 id="report-title" ref={reportRef} tabIndex={-1}>{report.test_status === "not_run" ? "Repository inspected. Tests were not run." : { success: "Supported checks came back clean.", failure: "Tests need your attention.", warning: "This setup needs a closer look.", error: "The inspection did not complete.", partial: "Some checks remain unjudged." }[state]}</h1>{report.message && <p className="report-message">{report.message}</p>}<p className="sr-only" role="status" aria-live="polite">Mission report ready. Validation {statusText(report.validation_status)}. Tests {statusText(report.test_status)}. Readiness {statusText(report.readiness_assessment)}.</p></div><div className="verdict-seal" aria-hidden="true">{state === "success" ? <Check /> : state === "warning" || state === "partial" ? <CircleAlert /> : <X />}</div></div>
    <div className="report-context">{report.repository && <code>{report.repository}</code>}{report.default_branch && <span>BRANCH <b>{report.default_branch}</b></span>}{report.language && <span>LANGUAGE <b>{report.language}</b></span>}{report.framework && <span>RUNNER <b>{report.framework}</b></span>}{typeof report.supported === "boolean" && <span>{report.supported ? "SUPPORTED" : "UNSUPPORTED"}</span>}</div>
    <div className="verdict-strip" aria-label="Validation summary">{[["VALIDATION", report.validation_status], ["TESTS", report.test_status], ["READINESS", report.readiness_assessment], ["CONFIGURATION", report.configuration_status]].filter(([, value]) => typeof value === "string" && value.length > 0).map(([label, value]) => <div key={label}><span>{label}</span><strong data-state={value || ""}>{statusText(value)}</strong></div>)}</div>
    <div className="report-grid"><section className="findings-panel" aria-labelledby="findings-title"><div className="panel-heading"><div><p className="eyebrow">EVIDENCE BOARD</p><h2 id="findings-title">Findings <span className="count-chip">{filtered.length}{filtered.length !== findings.length ? ` / ${findings.length}` : ""}</span></h2></div><div className="filter-group" role="group" aria-label="Filter findings">{(["all", "error", "warning", "info"] as FindingFilter[]).map((value) => <button key={value} className={filter === value ? "filter-button is-selected" : "filter-button"} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)}>{value === "all" ? "ALL" : value === "error" ? "ERRORS" : value === "warning" ? "WARNINGS" : "INFO"}</button>)}</div></div><div className="findings-list">{filtered.length ? filtered.map((item, index) => <FindingRow key={`${item.code}-${index}`} item={item} index={index} reduceMotion={reduceMotion} />) : <p className="empty-state">{findings.length ? "No findings in this severity group." : "The API returned no findings."}</p>}</div></section>
      <aside className="snapshot-panel" aria-labelledby="snapshot-title"><div className="panel-heading"><div><p className="eyebrow">REPOSITORY SCAN</p><h2 id="snapshot-title">Field snapshot</h2></div></div><dl className="repo-facts">{factRows.filter(([, value]) => value !== undefined && value !== null && value !== "").map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
        {configGroups}{configuration?.dependency_manifests && <p className="config-limitation">Dependency resolution: {statusText(configuration.dependency_manifests.dependency_resolution)}. Repository dependencies are not installed by RepoCheck.</p>}
      </aside></div>
    <details className="terminal-panel"><summary><span><b>TERMINAL RECORD</b><small>{report.execution_mode === "inspection_only" ? "NO TEST RUN IN INSPECTION-ONLY MODE" : report.status === "unsupported" ? "NO TEST RUN FOR THIS REPOSITORY" : "RAW OUTPUT FROM THE RESTRICTED RUN"}</small></span><span className="terminal-toggle" aria-hidden="true">+</span></summary><div className="terminal-content"><div className="terminal-inner"><div className="terminal-toolbar"><span>exit {report.exit_code ?? "not returned"} / {Number.isFinite(report.duration_seconds) ? `${report.duration_seconds?.toFixed(2)} s` : "test duration not reported"}</span>{logBlocks.length > 0 && <CopyButton value={logs} onCopied={onCopy}>COPY LOGS</CopyButton>}</div><pre className="log-output">{logs}</pre></div></div></details>
    <div className="report-actions"><div><p role="status" aria-live="polite">{copyMessage}</p><span>Every conclusion stays tied to a reported check.</span></div><div><CopyButton value={summary} onCopied={onCopy}>COPY SUMMARY</CopyButton><CopyButton value={JSON.stringify(report, null, 2)} onCopied={onCopy}>COPY REPORT</CopyButton><button className="button button-primary" onClick={newAnalysis}>NEW ANALYSIS <ArrowUpRight size={15} /></button></div></div><footer className="report-footer"><span>REPOCHECK / EVIDENCE OVER ASSUMPTION</span><a href="/docs" target="_blank" rel="noreferrer">API REFERENCE ↗</a></footer>
  </motion.section>;
}
