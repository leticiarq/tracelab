import { Fragment, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, evidenceContentUrl } from "../api";
import { Button, Icons, LoadingState } from "../components";
import type { AIReportAction, AIReportStyle, AIReportVersion, Evidence, Lab, Report } from "../types";

type NarrativeKey = "objective" | "vulnerability_description" | "resolution_steps" | "impact" | "mitigation" | "learnings";
const FIELDS: Array<{ key: NarrativeKey; label: string; placeholder: string }> = [
  { key: "objective", label: "Objetivo", placeholder: "O que deve ser alcançado neste laboratório?" },
  { key: "vulnerability_description", label: "Vulnerabilidade", placeholder: "Descreva a vulnerabilidade observada." },
  { key: "resolution_steps", label: "Etapas da resolução", placeholder: "Registre a metodologia e as etapas executadas." },
  { key: "impact", label: "Impacto", placeholder: "Qual é o impacto técnico ou de negócio?" },
  { key: "mitigation", label: "Mitigação", placeholder: "Como corrigir ou reduzir o risco?" },
  { key: "learnings", label: "Aprendizados", placeholder: "Quais foram os principais aprendizados?" },
];

export function ReportTab({ lab, onLabChange, notify }: { lab: Lab; onLabChange: (lab: Lab) => void; notify: (message: string) => void }) {
  const [report, setReport] = useState<Report | null>(null);
  const [markdown, setMarkdown] = useState("");
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [fields, setFields] = useState<Record<NarrativeKey, string>>(() => sourceFields(lab));
  const [mode, setMode] = useState<"code" | "preview">("code");
  const [reviewed, setReviewed] = useState(false);
  const [aiStyle, setAIStyle] = useState<AIReportStyle>("professional");
  const [aiVersions, setAIVersions] = useState<AIReportVersion[]>([]);
  const [suggestion, setSuggestion] = useState<AIReportVersion | null>(null);
  const [aiBusy, setAIBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.getReport(lab.id), api.listEvidences(lab.id), api.listAIReportVersions(lab.id)])
      .then(([saved, items, versions]) => {
        setReport(saved); setMarkdown(saved?.markdown || ""); setEvidences(items); setSelected(items.map((item) => item.id));
        setAIVersions(versions); setSuggestion(versions[0] || null);
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Falha ao carregar o relatório."))
      .finally(() => setLoading(false));
  }, [lab.id]);

  const dirty = report ? markdown !== report.markdown : Boolean(markdown);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault(); };
    window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const missing = FIELDS.filter((field) => !fields[field.key].trim()).map((field) => field.label);
  if (!evidences.length) missing.push("Evidências");
  const imageMap = useMemo(() => new Map(evidences.map((item, index) => [`evidence/${exportName(item, index + 1)}`, evidenceContentUrl(lab.id, item.id)])), [evidences, lab.id]);

  const generate = async (overwrite: boolean) => {
    if (overwrite && !window.confirm("Regenerar substituirá o Markdown atual, incluindo edições manuais. Deseja continuar?")) return;
    setBusy(true); setError("");
    try {
      const updatedLab = await api.updateLab(lab.id, Object.fromEntries(FIELDS.map(({ key }) => [key, fields[key].trim() || null])));
      onLabChange(updatedLab);
      const generated = await api.generateReport(lab.id, overwrite);
      setReport(generated); setMarkdown(generated.markdown); setMode("preview");
      notify(overwrite ? "Relatório regenerado com sucesso." : "Markdown gerado com sucesso.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao gerar o relatório."); }
    finally { setBusy(false); }
  };

  const save = async () => {
    setBusy(true); setError("");
    try { const saved = await api.saveReport(lab.id, markdown); setReport(saved); setMarkdown(saved.markdown); notify("Relatório salvo com sucesso."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao salvar o relatório."); }
    finally { setBusy(false); }
  };

  const exportZip = async () => {
    setBusy(true); setError("");
    try {
      const result = await api.exportReport(lab.id, selected, reviewed);
      const url = URL.createObjectURL(result.blob); const anchor = document.createElement("a");
      anchor.href = url; anchor.download = result.filename; anchor.click(); URL.revokeObjectURL(url);
      notify("ZIP exportado com sucesso.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao exportar o ZIP."); }
    finally { setBusy(false); }
  };

  const runAI = async (action: AIReportAction) => {
    setAIBusy(true); setError("");
    try {
      const generated = await api.generateAIReport(lab.id, action, aiStyle, selected);
      setSuggestion(generated); setAIVersions((current) => [generated, ...current]);
      notify("Sugestão gerada localmente. Revise antes de aceitar.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao gerar a sugestão."); }
    finally { setAIBusy(false); }
  };

  const cancelAI = async () => {
    try { await api.cancelAIOperation(); notify("Cancelamento solicitado."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao cancelar a geração."); }
  };

  const reviewSuggestion = async (action: "accept" | "reject") => {
    if (!suggestion) return;
    setError("");
    try {
      const reviewedSuggestion = await api.reviewAIReport(lab.id, suggestion.id, action);
      setSuggestion(reviewedSuggestion);
      setAIVersions((current) => current.map((item) => item.id === reviewedSuggestion.id ? reviewedSuggestion : item));
      if (action === "accept") { setMarkdown(reviewedSuggestion.suggested_text); setMode("code"); notify("Sugestão aceita no editor; salve quando terminar a revisão."); }
      else notify("Sugestão rejeitada; o conteúdo original foi preservado.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao revisar a sugestão."); }
  };

  if (loading) return <LoadingState label="Carregando relatório" />;
  return (
    <section className="report-tab" role="tabpanel">
      <div className="panel report-source">
        <div className="panel-heading"><div><h2>Conteúdo do relatório</h2><p>Os campos vazios serão omitidos. As anotações livres entram na metodologia sem serem alteradas.</p></div></div>
        <div className="report-fields">{FIELDS.map((field) => <label className="field" key={field.key}><span>{field.label}</span><textarea value={fields[field.key]} placeholder={field.placeholder} onChange={(event) => setFields((current) => ({ ...current, [field.key]: event.target.value }))} /></label>)}</div>
        {missing.length > 0 && <div className="report-warning"><Icons.alert className="h-5 w-5" /><span>Campos incompletos (serão omitidos): {missing.join(", ")}.</span></div>}
        <div className="report-actions"><Button onClick={() => void generate(false)} disabled={busy || Boolean(report)}>Gerar Markdown</Button>{report && <Button variant="secondary" onClick={() => void generate(true)} disabled={busy}>Regenerar</Button>}</div>
      </div>

      <div className="panel ai-report-panel">
        <div className="panel-heading"><div><h2>Assistente de IA local</h2><p>O Ollama só é chamado quando você escolher uma ação. Nenhuma sugestão substitui o conteúdo original automaticamente.</p></div>
          <label className="field ai-style"><span>Estilo</span><select aria-label="Estilo do relatório" value={aiStyle} onChange={(event) => setAIStyle(event.target.value as AIReportStyle)}><option value="professional">Técnico profissional</option><option value="github">Simples para GitHub</option><option value="study">Didático para estudo</option></select></label>
        </div>
        <div className="ai-report-actions">
          <Button variant="secondary" onClick={() => void runAI("improve_notes")} disabled={aiBusy}>Melhorar com IA</Button>
          <Button variant="secondary" onClick={() => void runAI("explain_vulnerability")} disabled={aiBusy}>Explicar vulnerabilidade</Button>
          <Button variant="secondary" onClick={() => void runAI("missing_information")} disabled={aiBusy}>Identificar informações faltantes</Button>
          <Button onClick={() => void runAI("generate_readme")} disabled={aiBusy}>Gerar README com IA</Button>
          {aiBusy && <Button variant="danger" onClick={() => void cancelAI()}>Cancelar</Button>}
        </div>
        {aiBusy && <div className="analysis-processing" role="status"><span className="spinner" />Gerando uma sugestão por vez no Ollama local…</div>}
        {suggestion && <div className="ai-comparison">
          <div className="comparison-heading"><strong>Revisão humana</strong><span>{suggestion.status === "suggested" ? "Aguardando decisão" : suggestion.status === "accepted" ? "Aceita" : "Rejeitada"}</span></div>
          <div className="comparison-columns"><label><span>Original preservado</span><textarea aria-label="Texto original" value={suggestion.original_text || "Nenhum texto original disponível."} readOnly /></label><label><span>Sugestão da IA</span><textarea aria-label="Texto sugerido" value={suggestion.suggested_text} readOnly /></label></div>
          {(suggestion.ambiguities.length > 0 || suggestion.questions.length > 0) && <div className="ai-review-notes">{suggestion.ambiguities.length > 0 && <div><strong>Ambiguidades</strong><ul>{suggestion.ambiguities.map((item) => <li key={item}>{item}</li>)}</ul></div>}{suggestion.questions.length > 0 && <div><strong>Perguntas sugeridas</strong><ul>{suggestion.questions.map((item) => <li key={item}>{item}</li>)}</ul></div>}</div>}
          {suggestion.status === "suggested" && <div className="ai-review-actions"><Button variant="secondary" onClick={() => void reviewSuggestion("reject")}>Rejeitar</Button><Button onClick={() => void reviewSuggestion("accept")}>Aceitar no editor</Button></div>}
        </div>}
        {aiVersions.length > 1 && <label className="field ai-history"><span>Versões geradas</span><select aria-label="Versões geradas" value={suggestion?.id || ""} onChange={(event) => setSuggestion(aiVersions.find((item) => item.id === Number(event.target.value)) || null)}>{aiVersions.map((item) => <option key={item.id} value={item.id}>{new Date(item.created_at).toLocaleString("pt-BR")} · {item.action}</option>)}</select></label>}
      </div>

      {error && <div className="inline-error" role="alert"><Icons.alert className="h-5 w-5" />{error}</div>}
      {(report || markdown) && <div className="panel report-workspace">
        <div className="report-toolbar"><div className="view-toggle" aria-label="Alternar visualização"><button className={mode === "code" ? "active" : ""} onClick={() => setMode("code")}>Código</button><button className={mode === "preview" ? "active" : ""} onClick={() => setMode("preview")}>Visualização</button></div><span className={dirty ? "save-state dirty" : "save-state"}><span />{dirty ? "Alterações não salvas" : report ? `Revisão ${report.revision}` : "Novo relatório"}</span></div>
        {mode === "code" ? <label className="report-editor"><span className="sr-only">Editor Markdown</span><textarea value={markdown} onChange={(event) => setMarkdown(event.target.value)} spellCheck={false} /></label> : <SafeMarkdown markdown={markdown} imageMap={imageMap} />}
        <div className="report-footer"><span>{markdown.length.toLocaleString("pt-BR")} caracteres</span><Button onClick={() => void save()} disabled={busy || !dirty || !markdown.trim()}>Salvar</Button></div>
      </div>}

      {report && <div className="panel export-panel"><div className="panel-heading"><div><h2>Exportar para GitHub</h2><p>Revise e selecione somente as evidências que devem fazer parte do ZIP.</p></div></div><div className="export-content">
        <fieldset><legend>Evidências selecionadas</legend>{evidences.length ? evidences.map((item) => <label key={item.id}><input type="checkbox" checked={selected.includes(item.id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} />{item.description || item.original_filename}</label>) : <p>Nenhuma evidência cadastrada.</p>}</fieldset>
        {report.sensitive_warnings.length > 0 && <div className="report-warning"><Icons.alert className="h-5 w-5" />O relatório contém: {report.sensitive_warnings.join(", ")}.</div>}
        <label className="review-check"><input type="checkbox" checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} />Revisei o README e as evidências e confirmei que não há informações sensíveis indevidas.</label>
        <Button onClick={() => void exportZip()} disabled={busy || dirty || !reviewed}>Exportar ZIP</Button>
      </div></div>}
    </section>
  );
}

function sourceFields(lab: Lab): Record<NarrativeKey, string> {
  return { objective: lab.objective || "", vulnerability_description: lab.vulnerability_description || "", resolution_steps: lab.resolution_steps || "", impact: lab.impact || "", mitigation: lab.mitigation || "", learnings: lab.learnings || "" };
}

function exportName(evidence: Evidence, position: number) {
  const extension: Record<string, string> = { "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "text/plain": ".txt", "message/http": ".http" };
  return `${evidence.mime_type.startsWith("image/") ? "image" : "evidence"}-${String(position).padStart(2, "0")}${extension[evidence.mime_type] || ""}`;
}

export function SafeMarkdown({ markdown, imageMap }: { markdown: string; imageMap: Map<string, string> }) {
  const blocks: ReactNode[] = []; const lines = markdown.split("\n"); let code: string[] | null = null; let paragraph: string[] = [];
  const flush = () => { if (paragraph.length) { blocks.push(<p key={`p-${blocks.length}`}>{paragraph.join("\n")}</p>); paragraph = []; } };
  for (const line of lines) {
    if (line.startsWith("```")) { flush(); if (code) { blocks.push(<pre key={`c-${blocks.length}`}><code>{code.join("\n")}</code></pre>); code = null; } else code = []; continue; }
    if (code) { code.push(line); continue; }
    if (!line.trim()) { flush(); continue; }
    const heading = line.match(/^(#{1,6})\s+(.+)$/); if (heading) { flush(); const level = heading[1].length; const Tag = `h${level}` as keyof JSX.IntrinsicElements; blocks.push(<Tag key={`h-${blocks.length}`}>{heading[2]}</Tag>); continue; }
    const image = line.match(/^!\[([^\]]*)\]\(([^)]+)\)$/); if (image) { flush(); const source = imageMap.get(image[2]); blocks.push(source ? <img key={`i-${blocks.length}`} src={source} alt={image[1]} /> : <p key={`i-${blocks.length}`}>Imagem não disponível: {image[1]}</p>); continue; }
    const bullet = line.match(/^[-*]\s+(.+)$/); if (bullet) { flush(); blocks.push(<ul key={`u-${blocks.length}`}><li>{bullet[1]}</li></ul>); continue; }
    paragraph.push(line);
  }
  flush(); if (code) blocks.push(<pre key={`c-${blocks.length}`}><code>{code.join("\n")}</code></pre>);
  return <article className="markdown-preview">{blocks.map((block, index) => <Fragment key={index}>{block}</Fragment>)}</article>;
}
