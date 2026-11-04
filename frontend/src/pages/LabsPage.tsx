import { useCallback, useEffect, useMemo, useState } from "react";

import type { Navigate } from "../App";
import { api } from "../api";
import { Button, ConfirmDialog, EmptyState, ErrorState, Icons, LoadingState, StatusBadge, Toast } from "../components";
import type { Category, Lab, LabStatus, Page, Platform } from "../types";
import { STATUS_LABELS } from "../types";

const EMPTY_PAGE: Page<Lab> = { items: [], total: 0, page: 1, page_size: 10, pages: 0 };

export function LabsPage({ navigate }: { navigate: Navigate }) {
  const [result, setResult] = useState(EMPTY_PAGE);
  const [platforms, setPlatforms] = useState<Platform[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [platformId, setPlatformId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [status, setStatus] = useState<LabStatus | "">("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Lab | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => { setDebouncedSearch(search.trim()); setPage(1); }, 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    Promise.all([api.listPlatforms(), api.listCategories()])
      .then(([platformData, categoryData]) => { setPlatforms(platformData.items); setCategories(categoryData.items); })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Falha ao carregar filtros."))
      .finally(() => setCatalogLoading(false));
  }, []);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      setResult(await api.listLabs({
        page, page_size: 10, search: debouncedSearch || undefined,
        platform_id: platformId ? Number(platformId) : undefined,
        category_id: categoryId ? Number(categoryId) : undefined,
        status: status || undefined,
      }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao listar laboratórios."); }
    finally { setLoading(false); }
  }, [page, debouncedSearch, platformId, categoryId, status]);

  useEffect(() => { void load(); }, [load]);

  const platformMap = useMemo(() => new Map(platforms.map((item) => [item.id, item.name])), [platforms]);
  const categoryMap = useMemo(() => new Map(categories.map((item) => [item.id, item.name])), [categories]);
  const visibleCategories = categories.filter((item) => !platformId || item.platform_id === null || item.platform_id === Number(platformId));
  const hasFilters = Boolean(search || platformId || categoryId || status);

  const resetFilters = () => { setSearch(""); setDebouncedSearch(""); setPlatformId(""); setCategoryId(""); setStatus(""); setPage(1); };
  const changePlatform = (value: string) => { setPlatformId(value); setCategoryId(""); setPage(1); };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.deleteLab(deleteTarget.id);
      setDeleteTarget(null); setToast("Laboratório excluído com sucesso.");
      window.setTimeout(() => setToast(""), 3500);
      if (result.items.length === 1 && page > 1) setPage(page - 1); else await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Falha ao excluir laboratório."); setDeleteTarget(null); }
    finally { setDeleting(false); }
  };

  return (
    <div className="page">
      <div className="page-heading">
        <div><p className="eyebrow">Workspace</p><h1>Meus laboratórios</h1><p>Organize, filtre e acompanhe todos os seus desafios.</p></div>
        <Button onClick={() => navigate("/labs/new")}><Icons.plus className="h-5 w-5" />Novo laboratório</Button>
      </div>

      <section className="filters" aria-label="Filtros de laboratórios">
        <label className="search-field"><span className="sr-only">Buscar por título</span><Icons.search className="h-5 w-5" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por título…" /></label>
        <label><span className="sr-only">Filtrar por plataforma</span><select value={platformId} disabled={catalogLoading} onChange={(event) => changePlatform(event.target.value)}><option value="">Todas as plataformas</option>{platforms.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label><span className="sr-only">Filtrar por categoria</span><select value={categoryId} disabled={catalogLoading} onChange={(event) => { setCategoryId(event.target.value); setPage(1); }}><option value="">Todas as categorias</option>{visibleCategories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <label><span className="sr-only">Filtrar por status</span><select value={status} onChange={(event) => { setStatus(event.target.value as LabStatus | ""); setPage(1); }}><option value="">Todos os status</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        {hasFilters && <button className="clear-filters" onClick={resetFilters}>Limpar filtros</button>}
      </section>

      {error ? <ErrorState message={error} retry={() => void load()} /> : loading ? <LoadingState label="Buscando laboratórios" /> : result.items.length === 0 ? (
        <section className="panel"><EmptyState title={hasFilters ? "Nenhum resultado encontrado" : "Nenhum laboratório cadastrado"} description={hasFilters ? "Tente ajustar ou limpar os filtros da busca." : "Cadastre seu primeiro laboratório para começar."} action={hasFilters ? <Button variant="secondary" onClick={resetFilters}>Limpar filtros</Button> : <Button onClick={() => navigate("/labs/new")}><Icons.plus className="h-5 w-5" />Novo laboratório</Button>} /></section>
      ) : (
        <section className="panel table-panel">
          <div className="result-summary"><strong>{result.total}</strong> {result.total === 1 ? "laboratório encontrado" : "laboratórios encontrados"}</div>
          <div className="table-wrap">
            <table><thead><tr><th>Laboratório</th><th>Plataforma</th><th>Categoria</th><th>Dificuldade</th><th>Status</th><th><span className="sr-only">Ações</span></th></tr></thead>
              <tbody>{result.items.map((lab) => <tr key={lab.id} onDoubleClick={() => navigate(`/labs/${lab.id}`)}><td><button className="lab-title-button" onClick={() => navigate(`/labs/${lab.id}`)}>{lab.title}<small>Adicionado em {formatDate(lab.created_at)}</small></button></td><td>{platformMap.get(lab.platform_id) || "—"}</td><td>{lab.category_id ? categoryMap.get(lab.category_id) || "—" : "—"}</td><td><span className="difficulty">{lab.difficulty || "Não definida"}</span></td><td><StatusBadge status={lab.status} /></td><td><div className="row-actions"><button onClick={() => navigate(`/labs/${lab.id}?edit=1`)} aria-label={`Editar ${lab.title}`} title="Editar"><Icons.edit className="h-4 w-4" /></button><button className="delete-action" onClick={() => setDeleteTarget(lab)} aria-label={`Excluir ${lab.title}`} title="Excluir"><Icons.trash className="h-4 w-4" /></button></div></td></tr>)}</tbody>
            </table>
          </div>
          {result.pages > 1 && <nav className="pagination" aria-label="Paginação"><Button variant="secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Anterior</Button><span>Página <strong>{page}</strong> de {result.pages}</span><Button variant="secondary" disabled={page === result.pages} onClick={() => setPage(page + 1)}>Próxima</Button></nav>}
        </section>
      )}
      {deleteTarget && <ConfirmDialog title="Excluir laboratório?" description={`“${deleteTarget.title}” e todas as suas anotações serão removidos permanentemente.`} confirmLabel="Excluir laboratório" busy={deleting} onCancel={() => setDeleteTarget(null)} onConfirm={() => void confirmDelete()} />}
      {toast && <Toast message={toast} />}
    </div>
  );
}

function formatDate(date: string) { return new Intl.DateTimeFormat("pt-BR").format(new Date(date)); }
