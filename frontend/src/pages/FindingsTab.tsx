import { useCallback, useEffect, useState } from "react";

import { api, evidenceContentUrl } from "../api";
import { Button, ConfirmDialog, EmptyState, ErrorState, Icons, LoadingState } from "../components";
import type { CVSSAssessment, Evidence, Finding, FindingInput, FindingStatus } from "../types";

const EMPTY: FindingInput = { title: "", category: null, cwe_id: null, description: "", technical_details: "", reproduction_steps: "", impact: "", mitigation: "", status: "open" };
const EMPTY_CVSS = { version: "3.1", vector: "", score: 0, severity: "", justification: "" };

export function FindingsTab({ labId, notify }: { labId: number; notify: (message: string) => void }) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<FindingInput>(EMPTY);
  const [cvssEnabled, setCVSSEnabled] = useState(false);
  const [cvss, setCVSS] = useState(EMPTY_CVSS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Finding | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [items, evidenceItems] = await Promise.all([api.listFindings(labId), api.listEvidences(labId)]);
      setFindings(items); setEvidences(evidenceItems);
      setSelectedId((current) => current && items.some((item) => item.id === current) ? current : items[0]?.id ?? null);
    } catch (reason) { setError(messageFrom(reason, "Falha ao carregar as vulnerabilidades.")); }
    finally { setLoading(false); }
  }, [labId]);

  useEffect(() => { void load(); }, [load]);
  const selected = findings.find((item) => item.id === selectedId) ?? null;
  useEffect(() => {
    if (creating) return;
    if (!selected) { setDraft(EMPTY); setCVSSEnabled(false); setCVSS(EMPTY_CVSS); return; }
    setDraft(toInput(selected));
    setCVSSEnabled(Boolean(selected.cvss_assessment));
    setCVSS(selected.cvss_assessment ? toCVSS(selected.cvss_assessment) : EMPTY_CVSS);
  }, [creating, selected]);

  const beginCreate = () => { setCreating(true); setSelectedId(null); setDraft(EMPTY); setCVSSEnabled(false); setCVSS(EMPTY_CVSS); };
  const save = async () => {
    if (!draft.title.trim()) { setError("Informe o título da vulnerabilidade."); return; }
    setSaving(true); setError("");
    try {
      let finding = creating
        ? await api.createFinding(labId, normalize(draft))
        : await api.updateFinding(labId, selected!.id, normalize(draft));
      if (cvssEnabled) {
        const assessment = await api.saveCVSS(labId, finding.id, cvss);
        finding = { ...finding, cvss_assessment: assessment };
      } else if (!creating && selected?.cvss_assessment) {
        await api.deleteCVSS(labId, finding.id);
        finding = { ...finding, cvss_assessment: null };
      }
      setFindings((items) => creating ? [...items, finding] : items.map((item) => item.id === finding.id ? finding : item));
      setCreating(false); setSelectedId(finding.id); notify("Vulnerabilidade salva com sucesso.");
    } catch (reason) { setError(messageFrom(reason, "Falha ao salvar a vulnerabilidade.")); }
    finally { setSaving(false); }
  };

  const remove = async () => {
    if (!pendingDelete) return;
    setSaving(true); setError("");
    try {
      await api.deleteFinding(labId, pendingDelete.id);
      const remaining = findings.filter((item) => item.id !== pendingDelete.id).map((item, display_order) => ({ ...item, display_order }));
      setFindings(remaining); setSelectedId(remaining[0]?.id ?? null); setPendingDelete(null);
      setEvidences((items) => items.map((item) => item.finding_id === pendingDelete.id ? { ...item, finding_id: null } : item));
      notify("Vulnerabilidade excluída; as evidências foram mantidas como gerais.");
    } catch (reason) { setError(messageFrom(reason, "Falha ao excluir a vulnerabilidade.")); }
    finally { setSaving(false); }
  };

  const move = async (finding: Finding, direction: -1 | 1) => {
    const index = findings.findIndex((item) => item.id === finding.id); const target = index + direction;
    if (target < 0 || target >= findings.length) return;
    const reordered = [...findings]; [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
    setFindings(reordered.map((item, display_order) => ({ ...item, display_order })));
    try { setFindings(await api.reorderFindings(labId, reordered.map((item) => item.id))); }
    catch (reason) { setError(messageFrom(reason, "Falha ao reordenar.")); void load(); }
  };

  if (loading) return <LoadingState label="Carregando vulnerabilidades" />;
  if (error && !findings.length && !creating) return <ErrorState message={error} retry={() => void load()} />;
  return <section className="findings-tab" role="tabpanel">
    <header className="findings-heading"><div><h2>Vulnerabilidades <span>{findings.length}</span></h2><p>Documente achados independentes sem tornar CVSS obrigatório.</p></div><Button onClick={beginCreate}><Icons.plus className="h-4 w-4" />Adicionar vulnerabilidade</Button></header>
    {error && <div className="inline-error" role="alert"><Icons.alert className="h-5 w-5" />{error}<button onClick={() => setError("")} aria-label="Fechar erro">×</button></div>}
    {!findings.length && !creating ? <div className="panel"><EmptyState icon={<Icons.alert className="h-7 w-7" />} title="Nenhuma vulnerabilidade" description="Este laboratório pode permanecer como exercício de aprendizagem, ou você pode adicionar o primeiro achado quando precisar." /><div className="empty-action"><Button onClick={beginCreate}>Adicionar primeira vulnerabilidade</Button></div></div> :
      <div className={`findings-layout ${findings.length <= 1 ? "single" : ""}`}>
        {findings.length > 0 && <div className="findings-list" aria-label="Lista de vulnerabilidades">{findings.map((item, index) => <article key={item.id} className={selectedId === item.id && !creating ? "finding-card selected" : "finding-card"}>
          <button className="finding-select" onClick={() => { setCreating(false); setSelectedId(item.id); }}><strong>{item.title}</strong><span>{item.category || "Sem categoria"} · {statusLabel(item.status)}</span>{item.cvss_assessment && <small className={`severity severity-${item.cvss_assessment.severity.toLowerCase()}`}>{item.cvss_assessment.score} · {item.cvss_assessment.severity}</small>}</button>
          <div className="finding-order"><button onClick={() => void move(item, -1)} disabled={index === 0} aria-label={`Mover ${item.title} para cima`}>↑</button><button onClick={() => void move(item, 1)} disabled={index === findings.length - 1} aria-label={`Mover ${item.title} para baixo`}>↓</button></div>
        </article>)}</div>}
        {(creating || selected) && <FindingEditor draft={draft} setDraft={setDraft} cvssEnabled={cvssEnabled} setCVSSEnabled={setCVSSEnabled} cvss={cvss} setCVSS={setCVSS} evidences={evidences.filter((item) => item.finding_id === selected?.id)} labId={labId} creating={creating} saving={saving} onSave={() => void save()} onCancel={() => { setCreating(false); setSelectedId(findings[0]?.id ?? null); }} onDelete={() => selected && setPendingDelete(selected)} />}
      </div>}
    {pendingDelete && <ConfirmDialog title="Excluir vulnerabilidade?" description={`“${pendingDelete.title}” será excluída. Suas evidências não serão apagadas e voltarão a ser evidências gerais do laboratório.`} confirmLabel="Excluir vulnerabilidade" busy={saving} onCancel={() => setPendingDelete(null)} onConfirm={() => void remove()} />}
  </section>;
}

function FindingEditor({ draft, setDraft, cvssEnabled, setCVSSEnabled, cvss, setCVSS, evidences, labId, creating, saving, onSave, onCancel, onDelete }: {
  draft: FindingInput; setDraft: (value: FindingInput) => void; cvssEnabled: boolean; setCVSSEnabled: (value: boolean) => void;
  cvss: typeof EMPTY_CVSS; setCVSS: (value: typeof EMPTY_CVSS) => void; evidences: Evidence[]; labId: number; creating: boolean; saving: boolean;
  onSave: () => void; onCancel: () => void; onDelete: () => void;
}) {
  const field = (key: keyof FindingInput, value: string) => setDraft({ ...draft, [key]: value });
  return <article className="panel finding-editor"><div className="panel-heading"><div><h2>{creating ? "Nova vulnerabilidade" : draft.title}</h2><p>{creating ? "Apenas o título é obrigatório." : "Alterações técnicas deste achado."}</p></div></div>
    <div className="finding-form-row"><label className="field"><span>Título *</span><input aria-label="Título da vulnerabilidade" value={draft.title} maxLength={200} onChange={(e) => field("title", e.target.value)} /></label><label className="field"><span>Status</span><select value={draft.status} onChange={(e) => field("status", e.target.value as FindingStatus)}><option value="open">Aberta</option><option value="confirmed">Confirmada</option><option value="remediated">Corrigida</option><option value="accepted_risk">Risco aceito</option></select></label></div>
    <div className="finding-form-row"><label className="field"><span>Categoria</span><input value={draft.category || ""} maxLength={120} onChange={(e) => field("category", e.target.value)} /></label><label className="field"><span>CWE</span><input value={draft.cwe_id || ""} placeholder="CWE-89" maxLength={20} onChange={(e) => field("cwe_id", e.target.value)} /></label></div>
    {([ ["description", "Descrição"], ["technical_details", "Anotações técnicas"], ["reproduction_steps", "Passos de reprodução"], ["impact", "Impacto"], ["mitigation", "Mitigação"] ] as Array<[keyof FindingInput, string]>).map(([key, label]) => <label className="field" key={key}><span>{label}</span><textarea value={String(draft[key] || "")} onChange={(e) => field(key, e.target.value)} /></label>)}
    <label className="review-check"><input type="checkbox" checked={cvssEnabled} onChange={(e) => setCVSSEnabled(e.target.checked)} />Adicionar avaliação CVSS informada manualmente</label>
    {cvssEnabled && <fieldset className="cvss-fields"><legend>CVSS opcional — nenhuma pontuação é recalculada</legend><div className="finding-form-row"><label className="field"><span>Versão</span><input value={cvss.version} onChange={(e) => setCVSS({ ...cvss, version: e.target.value })} /></label><label className="field"><span>Pontuação</span><input aria-label="Pontuação CVSS" type="number" min="0" max="10" step="0.1" value={cvss.score} onChange={(e) => setCVSS({ ...cvss, score: Number(e.target.value) })} /></label><label className="field"><span>Severidade</span><input value={cvss.severity} onChange={(e) => setCVSS({ ...cvss, severity: e.target.value })} /></label></div><label className="field"><span>Vetor</span><input value={cvss.vector} onChange={(e) => setCVSS({ ...cvss, vector: e.target.value })} /></label><label className="field"><span>Justificativa</span><textarea value={cvss.justification} onChange={(e) => setCVSS({ ...cvss, justification: e.target.value })} /></label></fieldset>}
    {!creating && <div className="finding-evidences"><h3>Evidências associadas <span>{evidences.length}</span></h3>{evidences.length ? <div className="finding-evidence-grid">{evidences.map((item) => <div key={item.id}>{item.mime_type.startsWith("image/") ? <img src={evidenceContentUrl(labId, item.id)} alt={item.description || item.original_filename} /> : <Icons.note className="h-7 w-7" />}<span>{item.description || item.original_filename}</span></div>)}</div> : <p>Associe evidências pela aba Evidências.</p>}</div>}
    <div className="finding-editor-actions">{!creating && <Button variant="danger" onClick={onDelete}>Excluir</Button>}<span /><Button variant="secondary" onClick={onCancel}>Cancelar</Button><Button onClick={onSave} disabled={saving}>{saving ? "Salvando…" : "Salvar vulnerabilidade"}</Button></div>
  </article>;
}

function toInput(finding: Finding): FindingInput { return { title: finding.title, category: finding.category, cwe_id: finding.cwe_id, description: finding.description, technical_details: finding.technical_details, reproduction_steps: finding.reproduction_steps, impact: finding.impact, mitigation: finding.mitigation, status: finding.status }; }
function normalize(value: FindingInput): FindingInput { return { ...value, title: value.title.trim(), category: value.category?.trim() || null, cwe_id: value.cwe_id?.trim() || null }; }
function toCVSS(value: CVSSAssessment) { return { version: value.version, vector: value.vector, score: value.score, severity: value.severity, justification: value.justification }; }
function statusLabel(status: FindingStatus) { return ({ open: "Aberta", confirmed: "Confirmada", remediated: "Corrigida", accepted_risk: "Risco aceito" })[status]; }
function messageFrom(reason: unknown, fallback: string) { return reason instanceof Error ? reason.message : fallback; }
