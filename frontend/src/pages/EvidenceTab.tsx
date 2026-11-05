import { useCallback, useEffect, useRef, useState } from "react";

import { api, evidenceContentUrl, evidenceDownloadUrl } from "../api";
import { Button, ConfirmDialog, EmptyState, ErrorState, Icons, LoadingState } from "../components";
import type { Evidence, Finding } from "../types";

const ACCEPT = ".png,.jpg,.jpeg,.webp,.txt,.http,image/png,image/jpeg,image/webp,text/plain,message/http";

export function EvidenceTab({
  labId,
  notify,
}: {
  labId: number;
  notify: (message: string) => void;
}) {
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [textContent, setTextContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Evidence | null>(null);
  const [description, setDescription] = useState("");
  const [stepLabel, setStepLabel] = useState("");
  const [findingId, setFindingId] = useState<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [items, findingItems] = await Promise.all([api.listEvidences(labId), api.listFindings(labId)]);
      setEvidences(items);
      setFindings(findingItems);
      setSelectedId((current) => current && items.some((item) => item.id === current) ? current : items[0]?.id ?? null);
    } catch (reason) { setError(messageFrom(reason, "Falha ao carregar as evidências.")); }
    finally { setLoading(false); }
  }, [labId]);

  useEffect(() => { void load(); }, [load]);
  const selected = evidences.find((item) => item.id === selectedId) ?? null;

  useEffect(() => {
    setDescription(selected?.description ?? "");
    setStepLabel(selected?.step_label ?? "");
    setFindingId(selected?.finding_id ?? null);
    setTextContent("");
    if (!selected || selected.mime_type.startsWith("image/")) return;
    const controller = new AbortController();
    fetch(evidenceContentUrl(labId, selected.id), { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Não foi possível abrir o arquivo textual.");
        return response.text();
      })
      .then(setTextContent)
      .catch((reason: unknown) => { if ((reason as Error).name !== "AbortError") setError(messageFrom(reason, "Falha ao abrir a evidência.")); });
    return () => controller.abort();
  }, [labId, selected]);

  const upload = async (files: FileList | File[]) => {
    const selectedFiles = Array.from(files);
    if (!selectedFiles.length) return;
    setUploading(true); setError("");
    try {
      const created = await api.uploadEvidences(labId, selectedFiles);
      const items = await api.listEvidences(labId);
      setEvidences(items); setSelectedId(created[0]?.id ?? null);
      notify(`${created.length} evidência${created.length === 1 ? " enviada" : "s enviadas"} com sucesso.`);
      if (inputRef.current) inputRef.current.value = "";
    } catch (reason) { setError(messageFrom(reason, "Falha ao enviar as evidências.")); }
    finally { setUploading(false); setDragging(false); }
  };

  const saveMetadata = async () => {
    if (!selected) return;
    setSaving(true); setError("");
    try {
      const updated = await api.updateEvidence(labId, selected.id, { description, step_label: stepLabel || null, finding_id: findingId });
      setEvidences((items) => items.map((item) => item.id === updated.id ? updated : item));
      notify("Nome, legenda e etapa salvos.");
    } catch (reason) { setError(messageFrom(reason, "Falha ao salvar os metadados.")); }
    finally { setSaving(false); }
  };

  const move = async (direction: -1 | 1) => {
    if (!selected) return;
    const index = evidences.findIndex((item) => item.id === selected.id);
    const destination = index + direction;
    if (destination < 0 || destination >= evidences.length) return;
    const reordered = [...evidences];
    [reordered[index], reordered[destination]] = [reordered[destination], reordered[index]];
    setEvidences(reordered.map((item, order) => ({ ...item, display_order: order })));
    try { setEvidences(await api.reorderEvidences(labId, reordered.map((item) => item.id))); }
    catch (reason) { setError(messageFrom(reason, "Falha ao reordenar.")); void load(); }
  };

  const remove = async () => {
    if (!pendingDelete) return;
    setSaving(true); setError("");
    try {
      await api.deleteEvidence(labId, pendingDelete.id);
      const remaining = evidences.filter((item) => item.id !== pendingDelete.id);
      setEvidences(remaining); setSelectedId(remaining[0]?.id ?? null); setPendingDelete(null);
      notify("Evidência excluída com sucesso.");
    } catch (reason) { setError(messageFrom(reason, "Falha ao excluir a evidência.")); }
    finally { setSaving(false); }
  };

  if (loading) return <LoadingState label="Carregando evidências" />;
  if (error && !evidences.length) return <ErrorState message={error} retry={() => void load()} />;

  return (
    <section className="evidence-tab" role="tabpanel">
      <header className="evidence-heading">
        <div><h2>Evidências <span>{evidences.length}</span></h2><p>Screenshots, textos e tráfego HTTP vinculados a este laboratório.</p></div>
      </header>
      {error && <div className="inline-error" role="alert"><Icons.alert className="h-5 w-5" />{error}<button onClick={() => setError("")} aria-label="Fechar erro">×</button></div>}
      <div
        className={`upload-zone ${dragging ? "dragging" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false); }}
        onDrop={(event) => { event.preventDefault(); void upload(event.dataTransfer.files); }}
      >
        <Icons.plus className="h-7 w-7" /><div><strong>{uploading ? "Enviando arquivos…" : "Arraste evidências para cá"}</strong><p>PNG, JPEG, WebP, TXT ou HTTP · até 10 MB por arquivo · máximo de 10 por envio</p></div>
        <Button onClick={() => inputRef.current?.click()} disabled={uploading}>Selecionar arquivos</Button>
        <input ref={inputRef} className="sr-only" aria-label="Selecionar evidências" type="file" multiple accept={ACCEPT} onChange={(event) => event.target.files && void upload(event.target.files)} />
      </div>

      {!evidences.length ? (
        <div className="panel"><EmptyState icon={<Icons.note className="h-7 w-7" />} title="Nenhuma evidência" description="Envie screenshots, arquivos de texto ou requisições HTTP para documentar as etapas do laboratório." /></div>
      ) : (
        <div className="evidence-layout">
          <div className="evidence-gallery" aria-label="Galeria de evidências">
            {evidences.map((item, index) => (
              <button key={item.id} className={`evidence-card ${selectedId === item.id ? "selected" : ""}`} onClick={() => setSelectedId(item.id)}>
                <div className="evidence-thumb">{item.mime_type.startsWith("image/") ? <img src={evidenceContentUrl(labId, item.id)} alt="" /> : <Icons.note className="h-7 w-7" />}</div>
                <span className="evidence-order">{index + 1}</span>
                <strong>{item.description || item.original_filename}</strong><small>{item.step_label || formatBytes(item.file_size)}</small>
              </button>
            ))}
          </div>
          {selected && (
            <article className="evidence-detail panel">
              <div className="evidence-viewer">
                {selected.mime_type.startsWith("image/") ? (
                  <button onClick={() => setPreview(true)} aria-label={`Ampliar ${selected.description || selected.original_filename}`}><img src={evidenceContentUrl(labId, selected.id)} alt={selected.description || selected.original_filename} /></button>
                ) : <pre>{textContent || "Carregando conteúdo…"}</pre>}
              </div>
              <div className="evidence-fields">
                <label className="field">Nome descritivo / legenda<input value={description} maxLength={2000} onChange={(event) => setDescription(event.target.value)} /></label>
                <label className="field">Etapa do laboratório<input value={stepLabel} maxLength={200} placeholder="Ex.: 02 · Exploração" onChange={(event) => setStepLabel(event.target.value)} /></label>
                <label className="field">Vulnerabilidade<select value={findingId ?? ""} onChange={(event) => setFindingId(event.target.value ? Number(event.target.value) : null)}><option value="">Evidência geral do laboratório</option>{findings.map((finding) => <option key={finding.id} value={finding.id}>{finding.title}</option>)}</select></label>
                <div className="evidence-file-meta"><span>{selected.original_filename}</span><span>{formatBytes(selected.file_size)} · SHA-256 {selected.sha256.slice(0, 12)}…</span></div>
                <div className="privacy-note"><Icons.alert className="h-5 w-5" /><span>Revise tokens, credenciais e dados pessoais antes de exportar ou compartilhar esta evidência.</span></div>
                <div className="evidence-actions">
                  <Button variant="secondary" onClick={() => void move(-1)} disabled={selected.display_order === 0} aria-label="Mover evidência para cima">↑</Button>
                  <Button variant="secondary" onClick={() => void move(1)} disabled={selected.display_order === evidences.length - 1} aria-label="Mover evidência para baixo">↓</Button>
                  <a className="button button-secondary" href={evidenceDownloadUrl(labId, selected.id)}>Download</a>
                  <Button variant="danger" onClick={() => setPendingDelete(selected)}>Excluir</Button>
                  <Button onClick={() => void saveMetadata()} disabled={saving || (description === selected.description && stepLabel === (selected.step_label || "") && findingId === selected.finding_id)}>{saving ? "Salvando…" : "Salvar"}</Button>
                </div>
              </div>
            </article>
          )}
        </div>
      )}
      {preview && selected?.mime_type.startsWith("image/") && <div className="evidence-lightbox" role="dialog" aria-modal="true" aria-label="Visualização ampliada" onClick={() => setPreview(false)}><button aria-label="Fechar visualização">×</button><img src={evidenceContentUrl(labId, selected.id)} alt={selected.description || selected.original_filename} /></div>}
      {pendingDelete && <ConfirmDialog title="Excluir evidência?" description={`O arquivo “${pendingDelete.description || pendingDelete.original_filename}” e seus metadados serão removidos permanentemente.`} confirmLabel="Excluir evidência" busy={saving} onCancel={() => setPendingDelete(null)} onConfirm={() => void remove()} />}
    </section>
  );
}

function formatBytes(value: number) { if (value < 1024) return `${value} B`; if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`; return `${(value / 1024 ** 2).toFixed(1)} MB`; }
function messageFrom(reason: unknown, fallback: string) { return reason instanceof Error ? reason.message : fallback; }
