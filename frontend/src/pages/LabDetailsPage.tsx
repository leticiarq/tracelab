import { useCallback, useEffect, useMemo, useState } from "react";

import type { Navigate } from "../App";
import { api } from "../api";
import { Button, EmptyState, ErrorState, Icons, LoadingState, StatusBadge, Toast } from "../components";
import type { Category, Lab, Platform } from "../types";
import { EvidenceTab } from "./EvidenceTab";

type Tab = "info" | "notes" | "evidence" | "report";

export function LabDetailsPage({ navigate, labId }: { navigate: Navigate; labId: number }) {
  const [lab, setLab] = useState<Lab | null>(null);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tab, setTab] = useState<Tab>("info");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [labData, platformData, categoryData] = await Promise.all([api.getLab(labId), api.listPlatforms(), api.listCategories()]);
      setLab(labData); setNotes(labData.notes); setPlatforms(platformData.items); setCategories(categoryData.items);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao abrir o laboratório."); }
    finally { setLoading(false); }
  }, [labId]);

  useEffect(() => { void load(); }, [load]);
  const dirty = lab !== null && notes !== lab.notes;
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault(); };
    window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const platformMap = useMemo(() => new Map(platforms.map((item) => [item.id, item.name])), [platforms]);
  const categoryMap = useMemo(() => new Map(categories.map((item) => [item.id, item.name])), [categories]);

  const saveNotes = async () => {
    if (!lab) return; setSaving(true); setError("");
    try { const updated = await api.updateLab(lab.id, { notes }); setLab(updated); setNotes(updated.notes); setToast("Anotações salvas com sucesso."); window.setTimeout(() => setToast(""), 3500); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao salvar as anotações."); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="page"><LoadingState label="Abrindo laboratório" /></div>;
  if (error && !lab) return <div className="page"><ErrorState message={error} retry={() => void load()} /></div>;
  if (!lab) return null;

  const tabs: Array<{ id: Tab; label: string }> = [{ id: "info", label: "Informações" }, { id: "notes", label: "Anotações" }, { id: "evidence", label: "Evidências" }, { id: "report", label: "Relatório" }];

  return (
    <div className="page details-page">
      <button className="back-button" onClick={() => navigate("/labs")}><span aria-hidden="true">←</span> Meus laboratórios</button>
      <header className="details-header">
        <div className="details-title"><span className="lab-avatar large">{lab.title.slice(0, 2).toUpperCase()}</span><div><div className="details-meta"><StatusBadge status={lab.status} /><span>Atualizado em {formatDate(lab.updated_at)}</span></div><h1>{lab.title}</h1><p>{platformMap.get(lab.platform_id) || "Plataforma não encontrada"}{lab.category_id ? ` · ${categoryMap.get(lab.category_id) || "Categoria não encontrada"}` : ""}</p></div></div>
        <Button variant="secondary" onClick={() => navigate(`/labs/${lab.id}?edit=1`)}><Icons.edit className="h-4 w-4" />Editar</Button>
      </header>
      <div className="tabs" role="tablist" aria-label="Conteúdo do laboratório">{tabs.map((item) => <button key={item.id} role="tab" aria-selected={tab === item.id} className={tab === item.id ? "active" : ""} onClick={() => setTab(item.id)}>{item.label}{item.id === "notes" && dirty && <span className="dirty-dot" aria-label="Alterações não salvas" />}</button>)}</div>

      {error && <div className="inline-error" role="alert"><Icons.alert className="h-5 w-5" />{error}</div>}
      {tab === "info" && <InfoTab lab={lab} platform={platformMap.get(lab.platform_id)} category={lab.category_id ? categoryMap.get(lab.category_id) : undefined} />}
      {tab === "notes" && (
        <section className="panel notes-panel" role="tabpanel">
          <div className="notes-heading"><div><h2>Anotações de resolução</h2><p>Registre comandos, código, requisições e observações livremente.</p></div><div className={dirty ? "save-state dirty" : "save-state"}><span />{dirty ? "Alterações não salvas" : "Tudo salvo"}</div></div>
          <label className="notes-editor"><span className="sr-only">Anotações do laboratório</span><textarea value={notes} onChange={(event) => setNotes(event.target.value)} spellCheck={false} placeholder={"# Reconhecimento\n\nnmap -sV 10.10.10.10\n\n## Observações\n..."} /></label>
          <div className="notes-footer"><span>{notes.length.toLocaleString("pt-BR")} caracteres</span><Button onClick={() => void saveNotes()} disabled={!dirty || saving}>{saving ? "Salvando…" : "Salvar anotações"}</Button></div>
        </section>
      )}
      {tab === "evidence" && <EvidenceTab labId={lab.id} notify={(message) => { setToast(message); window.setTimeout(() => setToast(""), 3500); }} />}
      {tab === "report" && <section className="panel" role="tabpanel"><EmptyState icon={<Icons.note className="h-7 w-7" />} title="Relatório em breve" description="A composição do relatório será implementada em uma próxima etapa." /></section>}
      {toast && <Toast message={toast} />}
    </div>
  );
}

function InfoTab({ lab, platform, category }: { lab: Lab; platform?: string; category?: string }) {
  const items = [{ label: "Plataforma", value: platform || "—" }, { label: "Categoria", value: category || "Sem categoria" }, { label: "Dificuldade", value: lab.difficulty || "Não definida" }, { label: "Criado em", value: formatDate(lab.created_at) }, { label: "Resolvido em", value: lab.solved_at ? formatDate(lab.solved_at) : "—" }];
  return <section className="panel info-panel" role="tabpanel"><div className="panel-heading"><div><h2>Informações do laboratório</h2><p>Dados gerais e referência do desafio.</p></div></div><dl>{items.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}</dl>{lab.source_url && <a className="source-link" href={lab.source_url} target="_blank" rel="noreferrer"><span><small>Link do laboratório</small>{lab.source_url}</span><Icons.external className="h-5 w-5" /></a>}</section>;
}

function formatDate(date: string) { return new Intl.DateTimeFormat("pt-BR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(date)); }
