import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "../api";
import { Icons } from "../components";
import type { AIGeneration, AIModel, AISettings, AIStatus } from "../types";

export function AISettingsPage() {
  const [settings, setSettings] = useState<AISettings | null>(null);
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<"connection" | "generation" | "settings" | null>(null);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AIGeneration | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const current = await api.getAISettings();
      setSettings(current);
      const currentStatus = await api.getAIStatus();
      setStatus(currentStatus);
      setModels(current.enabled && currentStatus.available ? await api.listAIModels() : []);
    } catch (cause) { setError(message(cause)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const toggleEnabled = async () => {
    if (!settings) return;
    setAction("settings"); setError(""); setResult(null);
    try {
      const updated = await api.updateAISettings({ enabled: !settings.enabled });
      setSettings(updated);
      const currentStatus = await api.getAIStatus();
      setStatus(currentStatus);
      setModels(updated.enabled && currentStatus.available ? await api.listAIModels() : []);
    } catch (cause) { setError(message(cause)); }
    finally { setAction(null); }
  };

  const selectModel = async (model: string) => {
    setAction("settings"); setError(""); setResult(null);
    try { setSettings(await api.updateAISettings({ model })); setStatus(await api.getAIStatus()); }
    catch (cause) { setError(message(cause)); }
    finally { setAction(null); }
  };

  const testConnection = async () => {
    setAction("connection"); setError(""); setResult(null);
    try {
      const currentStatus = await api.testAIConnection();
      setStatus(currentStatus);
      if (!currentStatus.available) setError(currentStatus.error || "O Ollama não está disponível.");
      else setModels(await api.listAIModels());
    } catch (cause) { setError(message(cause)); }
    finally { setAction(null); }
  };

  const testGeneration = async () => {
    setAction("generation"); setError(""); setResult(null);
    try { setResult(await api.testAIGeneration()); }
    catch (cause) { setError(message(cause)); }
    finally { setAction(null); }
  };

  const cancelGeneration = async () => {
    try {
      const response = await api.cancelAIOperation();
      if (!response.cancelled) setError("Nenhuma operação de IA estava em andamento.");
    } catch (cause) { setError(message(cause)); }
  };

  if (loading) return <main className="page"><p className="loading-state">Carregando configurações de IA…</p></main>;
  if (!settings) return <main className="page"><ErrorMessage text={error || "Não foi possível carregar as configurações."} /><button className="button button-secondary" onClick={() => void load()}>Tentar novamente</button></main>;

  const selected = models.find((model) => model.name === settings.model);
  const online = settings.enabled && Boolean(status?.available);

  return (
    <div className="page ai-settings-page">
      <header className="page-heading"><div><p className="eyebrow">Execução exclusivamente local</p><h1>Configurações de IA</h1><p>Conecte o TraceLab ao Ollama sem enviar dados para serviços externos.</p></div><span className={`ai-status-pill ${online ? "online" : "offline"}`}><span />{!settings.enabled ? "Desativada" : online ? "Ollama disponível" : "Ollama indisponível"}</span></header>
      {error && <ErrorMessage text={error} />}
      <section className="panel ai-settings-panel">
        <div className="panel-heading"><div><h2>Integração local</h2><p>A aplicação continua funcional quando esta opção está desligada ou o Ollama está offline.</p></div><label className="switch"><input type="checkbox" checked={settings.enabled} disabled={action !== null} onChange={() => void toggleEnabled()} /><span /><b>{settings.enabled ? "Ativada" : "Desativada"}</b></label></div>
        <div className="ai-config-grid">
          <div><span className="config-label">Servidor</span><strong>{settings.base_url}</strong><small>{status?.version ? `Ollama ${status.version}` : "Versão não identificada"}</small></div>
          <label className="field"><span>Modelo selecionado</span><select value={settings.model} disabled={!online || action !== null || models.length === 0} onChange={(event) => void selectModel(event.target.value)}>{!models.some((model) => model.name === settings.model) && <option value={settings.model}>{settings.model} (não encontrado)</option>}{models.map((model) => <option key={model.name} value={model.name}>{model.name}</option>)}</select></label>
          <div><span className="config-label">Tempo limite</span><strong>{settings.timeout_seconds} segundos</strong><small>Configurável por variável de ambiente</small></div>
          <div><span className="config-label">Descarregamento</span><strong>{settings.keep_alive}</strong><small>Modelo liberado após o período sem uso</small></div>
        </div>
        <div className="capability-row"><Capability label="Texto" supported={status?.capabilities?.text ?? selected?.capabilities?.text ?? false} /><Capability label="Imagens" supported={status?.capabilities?.images ?? selected?.capabilities?.images ?? false} /><span>{models.length} {models.length === 1 ? "modelo instalado" : "modelos instalados"}</span></div>
        <div className="ai-actions"><button className="button button-secondary" disabled={!settings.enabled || action !== null} onClick={() => void testConnection()}>{action === "connection" ? "Testando…" : "Testar conexão"}</button>{action === "generation" ? <button className="button button-danger" onClick={() => void cancelGeneration()}>Cancelar geração</button> : <button className="button button-primary" disabled={!online || !status?.selected_model_installed || action !== null} onClick={() => void testGeneration()}>Testar geração</button>}</div>
      </section>
      {result && <section className="panel generation-result" aria-live="polite"><div><Icons.check className="h-5 w-5" /><strong>Geração concluída com {result.model}</strong></div><p>{result.text}</p></section>}
      <section className="ai-local-note"><Icons.alert className="h-5 w-5" /><div><strong>Privacidade e recursos</strong><p>Nenhum arquivo é analisado automaticamente. As operações são iniciadas manualmente, uma por vez, e podem ser canceladas. O TraceLab não baixa modelos.</p></div></section>
    </div>
  );
}

function Capability({ label, supported }: { label: string; supported: boolean }) { return <span className={supported ? "capability supported" : "capability unsupported"}>{supported ? <Icons.check className="h-4 w-4" /> : <Icons.close className="h-4 w-4" />}{label}</span>; }
function ErrorMessage({ text }: { text: string }) { return <div className="inline-error" role="alert"><Icons.alert className="h-5 w-5" />{text}</div>; }
function message(cause: unknown) { return cause instanceof ApiError || cause instanceof Error ? cause.message : "Não foi possível concluir a operação."; }
