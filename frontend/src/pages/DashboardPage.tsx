import { useCallback, useEffect, useMemo, useState } from "react";

import type { Navigate } from "../App";
import { api, listAllLabs } from "../api";
import { Button, EmptyState, ErrorState, Icons, LoadingState, StatusBadge } from "../components";
import type { Lab, Platform } from "../types";

export function DashboardPage({ navigate }: { navigate: Navigate }) {
  const [labs, setLabs] = useState<Lab[]>([]);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [labData, platformData] = await Promise.all([listAllLabs(), api.listPlatforms()]);
      setLabs(labData); setPlatforms(platformData.items);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Falha ao carregar o dashboard.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const platformMap = useMemo(() => new Map(platforms.map((item) => [item.id, item.name])), [platforms]);
  const distribution = useMemo(() => {
    const counts = new Map<number, number>();
    labs.forEach((lab) => counts.set(lab.platform_id, (counts.get(lab.platform_id) || 0) + 1));
    return [...counts.entries()].map(([id, count]) => ({ id, name: platformMap.get(id) || "Plataforma removida", count })).sort((a, b) => b.count - a.count);
  }, [labs, platformMap]);
  const maxPlatform = Math.max(...distribution.map((item) => item.count), 1);

  if (loading) return <Page><LoadingState label="Preparando seu dashboard" /></Page>;
  if (error) return <Page><ErrorState message={error} retry={() => void load()} /></Page>;

  const cards = [
    { label: "Total de laboratórios", value: labs.length, color: "violet" },
    { label: "Em andamento", value: labs.filter((lab) => lab.status === "in_progress").length, color: "cyan" },
    { label: "Resolvidos", value: labs.filter((lab) => lab.status === "solved").length, color: "emerald" },
    { label: "Documentados", value: labs.filter((lab) => lab.status === "documented").length, color: "amber" },
  ];

  return (
    <Page>
      <div className="page-heading">
        <div><p className="eyebrow">Visão geral</p><h1>Dashboard</h1><p>Acompanhe seu progresso e retome de onde parou.</p></div>
        <Button onClick={() => navigate("/labs/new")}><Icons.plus className="h-5 w-5" />Novo laboratório</Button>
      </div>

      <section className="metric-grid" aria-label="Resumo dos laboratórios">
        {cards.map((card) => <article className={`metric-card metric-${card.color}`} key={card.label}><span>{card.label}</span><strong>{card.value}</strong><div /></article>)}
      </section>

      {labs.length === 0 ? (
        <section className="panel"><EmptyState title="Seu workspace está pronto" description="Cadastre o primeiro laboratório para começar a acompanhar sua evolução." action={<Button onClick={() => navigate("/labs/new")}><Icons.plus className="h-5 w-5" />Cadastrar laboratório</Button>} /></section>
      ) : (
        <div className="dashboard-grid">
          <section className="panel">
            <div className="panel-heading"><div><h2>Laboratórios recentes</h2><p>Últimos itens adicionados</p></div><button className="text-button" onClick={() => navigate("/labs")}>Ver todos <Icons.arrow className="h-4 w-4" /></button></div>
            <div className="recent-list">
              {labs.slice(0, 5).map((lab) => (
                <button className="recent-item" key={lab.id} onClick={() => navigate(`/labs/${lab.id}`)}>
                  <span className="lab-avatar">{lab.title.slice(0, 2).toUpperCase()}</span>
                  <span className="recent-main"><strong>{lab.title}</strong><small>{platformMap.get(lab.platform_id) || "—"} · {formatDate(lab.created_at)}</small></span>
                  <StatusBadge status={lab.status} /><Icons.arrow className="h-4 w-4 recent-arrow" />
                </button>
              ))}
            </div>
          </section>
          <section className="panel">
            <div className="panel-heading"><div><h2>Por plataforma</h2><p>Distribuição do seu estudo</p></div></div>
            <div className="distribution-list">
              {distribution.map((item) => (
                <div className="distribution-item" key={item.id}>
                  <div><span>{item.name}</span><strong>{item.count}</strong></div>
                  <div className="progress-track"><span style={{ width: `${(item.count / maxPlatform) * 100}%` }} /></div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </Page>
  );
}

function Page({ children }: { children: React.ReactNode }) {
  return <div className="page dashboard-page">{children}</div>;
}

function formatDate(date: string) {
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(new Date(date));
}
