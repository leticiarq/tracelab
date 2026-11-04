import { useEffect, useMemo, useState } from "react";

import type { Navigate } from "../App";
import { api } from "../api";
import { Button, ErrorState, Icons, LoadingState } from "../components";
import type { Category, LabInput, LabStatus, Platform } from "../types";
import { DIFFICULTIES, STATUS_LABELS } from "../types";

const EMPTY_FORM: LabInput = { title: "", platform_id: 0, category_id: null, source_url: null, difficulty: null, status: "todo" };

export function LabFormPage({ navigate, labId }: { navigate: Navigate; labId?: number }) {
  const [form, setForm] = useState<LabInput>(EMPTY_FORM);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [catalogMode, setCatalogMode] = useState<"platform" | "category" | null>(null);

  useEffect(() => {
    const requests = [api.listPlatforms(), api.listCategories(), ...(labId ? [api.getLab(labId)] : [])] as const;
    Promise.all(requests)
      .then((data) => {
        setPlatforms(data[0].items); setCategories(data[1].items);
        const lab = data[2];
        if (lab && "title" in lab) setForm({ title: lab.title, platform_id: lab.platform_id, category_id: lab.category_id, source_url: lab.source_url, difficulty: lab.difficulty, status: lab.status });
        else if (data[0].items.length) setForm((current) => ({ ...current, platform_id: data[0].items[0].id }));
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Falha ao preparar o formulário."))
      .finally(() => setLoading(false));
  }, [labId]);

  const visibleCategories = useMemo(() => categories.filter((item) => item.platform_id === null || item.platform_id === form.platform_id), [categories, form.platform_id]);
  const setValue = <K extends keyof LabInput>(key: K, value: LabInput[K]) => { setForm((current) => ({ ...current, [key]: value })); setFieldErrors((current) => ({ ...current, [key]: "" })); };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const errors: Record<string, string> = {};
    if (!form.title.trim()) errors.title = "Informe um título.";
    if (!form.platform_id) errors.platform_id = "Selecione ou crie uma plataforma.";
    if (form.source_url && !/^https?:\/\//i.test(form.source_url)) errors.source_url = "Use uma URL iniciada por http:// ou https://.";
    if (Object.keys(errors).length) { setFieldErrors(errors); return; }
    setSaving(true); setError("");
    try {
      const payload = { ...form, title: form.title.trim(), source_url: form.source_url?.trim() || null, difficulty: form.difficulty || null };
      const saved = labId ? await api.updateLab(labId, payload) : await api.createLab(payload);
      navigate(`/labs/${saved.id}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível salvar o laboratório."); }
    finally { setSaving(false); }
  };

  const addPlatform = async (data: { name: string; website_url: string }) => {
    const platform = await api.createPlatform(data);
    setPlatforms((items) => [...items, platform]); setForm((current) => ({ ...current, platform_id: platform.id, category_id: null })); setCatalogMode(null);
  };
  const addCategory = async (name: string) => {
    const category = await api.createCategory({ name, platform_id: form.platform_id });
    setCategories((items) => [...items, category]); setForm((current) => ({ ...current, category_id: category.id })); setCatalogMode(null);
  };

  if (loading) return <div className="page"><LoadingState label={labId ? "Carregando laboratório" : "Preparando formulário"} /></div>;
  if (error && !platforms.length && !labId) return <div className="page"><ErrorState message={error} /></div>;

  return (
    <div className="page form-page">
      <button className="back-button" onClick={() => navigate(labId ? `/labs/${labId}` : "/labs")}><span aria-hidden="true">←</span> Voltar</button>
      <div className="page-heading compact"><div><p className="eyebrow">{labId ? "Editar registro" : "Novo registro"}</p><h1>{labId ? "Editar laboratório" : "Novo laboratório"}</h1><p>Registre os dados essenciais. Você poderá adicionar anotações nos detalhes.</p></div></div>
      <form className="lab-form" onSubmit={(event) => void submit(event)} noValidate>
        <section className="panel form-panel">
          <div className="section-heading"><span>01</span><div><h2>Informações gerais</h2><p>Identifique o laboratório e sua origem.</p></div></div>
          {error && <div className="inline-error" role="alert"><Icons.alert className="h-5 w-5" />{error}</div>}
          <div className="form-grid">
            <label className="field full"><span>Título <b>*</b></span><input autoFocus value={form.title} onChange={(event) => setValue("title", event.target.value)} placeholder="Ex.: Web cache poisoning" aria-invalid={Boolean(fieldErrors.title)} />{fieldErrors.title && <small>{fieldErrors.title}</small>}</label>
            <label className="field"><span>Plataforma <b>*</b></span><div className="field-with-action"><select value={form.platform_id || ""} onChange={(event) => { setValue("platform_id", Number(event.target.value)); setValue("category_id", null); }} aria-invalid={Boolean(fieldErrors.platform_id)}><option value="">Selecione</option>{platforms.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button type="button" aria-label="Criar plataforma" title="Criar plataforma" onClick={() => setCatalogMode("platform")}><Icons.plus className="h-5 w-5" /></button></div>{fieldErrors.platform_id && <small>{fieldErrors.platform_id}</small>}</label>
            <label className="field"><span>Categoria</span><div className="field-with-action"><select value={form.category_id || ""} disabled={!form.platform_id} onChange={(event) => setValue("category_id", event.target.value ? Number(event.target.value) : null)}><option value="">Sem categoria</option>{visibleCategories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button type="button" disabled={!form.platform_id} aria-label="Criar categoria" title="Criar categoria" onClick={() => setCatalogMode("category")}><Icons.plus className="h-5 w-5" /></button></div></label>
            <label className="field full"><span>Link do laboratório</span><input type="url" value={form.source_url || ""} onChange={(event) => setValue("source_url", event.target.value)} placeholder="https://…" aria-invalid={Boolean(fieldErrors.source_url)} />{fieldErrors.source_url && <small>{fieldErrors.source_url}</small>}</label>
          </div>
        </section>
        <section className="panel form-panel">
          <div className="section-heading"><span>02</span><div><h2>Classificação</h2><p>Defina a dificuldade e o estágio atual.</p></div></div>
          <div className="form-grid">
            <label className="field"><span>Dificuldade</span><select value={form.difficulty || ""} onChange={(event) => setValue("difficulty", event.target.value || null)}><option value="">Não definida</option>{DIFFICULTIES.map((item) => <option key={item} value={item.toLowerCase()}>{item}</option>)}</select></label>
            <label className="field"><span>Status</span><select value={form.status} onChange={(event) => setValue("status", event.target.value as LabStatus)}>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          </div>
        </section>
        <div className="form-actions"><Button type="button" variant="secondary" onClick={() => navigate(labId ? `/labs/${labId}` : "/labs")}>Cancelar</Button><Button type="submit" disabled={saving}>{saving ? "Salvando…" : labId ? "Salvar alterações" : "Criar laboratório"}</Button></div>
      </form>
      {catalogMode && <CatalogDialog mode={catalogMode} platformName={platforms.find((item) => item.id === form.platform_id)?.name} onClose={() => setCatalogMode(null)} onPlatform={addPlatform} onCategory={addCategory} />}
    </div>
  );
}

function CatalogDialog({ mode, platformName, onClose, onPlatform, onCategory }: { mode: "platform" | "category"; platformName?: string; onClose: () => void; onPlatform: (data: { name: string; website_url: string }) => Promise<void>; onCategory: (name: string) => Promise<void> }) {
  const [name, setName] = useState(""); const [url, setUrl] = useState(""); const [saving, setSaving] = useState(false); const [error, setError] = useState("");
  const submit = async (event: React.FormEvent) => { event.preventDefault(); if (!name.trim()) { setError("Informe um nome."); return; } if (mode === "platform" && !/^https?:\/\//i.test(url)) { setError("Informe o site com http:// ou https://."); return; } setSaving(true); setError(""); try { if (mode === "platform") await onPlatform({ name: name.trim(), website_url: url.trim() }); else await onCategory(name.trim()); } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível criar o item."); } finally { setSaving(false); } };
  return <div className="dialog-backdrop"><form className="dialog catalog-dialog" role="dialog" aria-modal="true" aria-labelledby="catalog-title" onSubmit={(event) => void submit(event)}><button type="button" className="dialog-close" onClick={onClose} aria-label="Fechar"><Icons.close className="h-5 w-5" /></button><h2 id="catalog-title">Nova {mode === "platform" ? "plataforma" : "categoria"}</h2><p>{mode === "platform" ? "Cadastre a origem dos seus laboratórios." : `Adicione uma categoria para ${platformName || "a plataforma selecionada"}.`}</p><label className="field"><span>Nome <b>*</b></span><input autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder={mode === "platform" ? "Ex.: Hack The Box" : "Ex.: Web"} /></label>{mode === "platform" && <label className="field"><span>Site <b>*</b></span><input type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://…" /></label>}{error && <div className="inline-error" role="alert">{error}</div>}<div className="dialog-actions"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button type="submit" disabled={saving}>{saving ? "Criando…" : "Criar"}</Button></div></form></div>;
}
