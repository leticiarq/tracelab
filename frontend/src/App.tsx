import { useEffect, useState } from "react";

import { Icons } from "./components";
import { DashboardPage } from "./pages/DashboardPage";
import { LabDetailsPage } from "./pages/LabDetailsPage";
import { LabFormPage } from "./pages/LabFormPage";
import { LabsPage } from "./pages/LabsPage";

export type Navigate = (path: string) => void;

function App() {
  const [path, setPath] = useState(() => window.location.pathname + window.location.search);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname + window.location.search);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const navigate: Navigate = (nextPath) => {
    window.history.pushState({}, "", nextPath);
    setPath(nextPath);
    setMobileOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const pathname = path.split("?")[0];
  const labMatch = pathname.match(/^\/labs\/(\d+)$/);
  const isEdit = new URLSearchParams(path.split("?")[1] || "").get("edit") === "1";
  const activeSection = pathname === "/" ? "dashboard" : "labs";

  let content;
  if (pathname === "/") content = <DashboardPage navigate={navigate} />;
  else if (pathname === "/labs") content = <LabsPage navigate={navigate} />;
  else if (pathname === "/labs/new") content = <LabFormPage navigate={navigate} />;
  else if (labMatch && isEdit) content = <LabFormPage navigate={navigate} labId={Number(labMatch[1])} />;
  else if (labMatch) content = <LabDetailsPage navigate={navigate} labId={Number(labMatch[1])} />;
  else content = <NotFound navigate={navigate} />;

  const link = (event: React.MouseEvent<HTMLAnchorElement>, to: string) => {
    if (!event.ctrlKey && !event.metaKey && !event.shiftKey) {
      event.preventDefault();
      navigate(to);
    }
  };

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Pular para o conteúdo</a>
      <header className="mobile-header">
        <a href="/" className="brand" onClick={(event) => link(event, "/")}><Brand /></a>
        <button className="icon-button" onClick={() => setMobileOpen((open) => !open)} aria-label="Abrir menu" aria-expanded={mobileOpen}>
          {mobileOpen ? <Icons.close className="h-6 w-6" /> : <Icons.menu className="h-6 w-6" />}
        </button>
      </header>
      {mobileOpen && <button className="sidebar-scrim" aria-label="Fechar menu" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <a href="/" className="brand desktop-brand" onClick={(event) => link(event, "/")}><Brand /></a>
        <nav aria-label="Navegação principal">
          <a href="/" className={activeSection === "dashboard" ? "nav-link active" : "nav-link"} onClick={(event) => link(event, "/")}><Icons.grid className="h-5 w-5" />Dashboard</a>
          <a href="/labs" className={activeSection === "labs" ? "nav-link active" : "nav-link"} onClick={(event) => link(event, "/labs")}><Icons.flask className="h-5 w-5" />Meus laboratórios</a>
        </nav>
        <div className="sidebar-bottom">
          <a className="button button-primary w-full" href="/labs/new" onClick={(event) => link(event, "/labs/new")}><Icons.plus className="h-5 w-5" />Novo laboratório</a>
          <p><span className="api-dot" />API local</p>
        </div>
      </aside>
      <main id="main-content" className="main-content">{content}</main>
    </div>
  );
}

function Brand() {
  return <><span className="brand-mark"><Icons.flask className="h-6 w-6" /></span><span>Trace<span>Lab</span></span></>;
}

function NotFound({ navigate }: { navigate: Navigate }) {
  return <div className="not-found"><span>404</span><h1>Página não encontrada</h1><p>O endereço acessado não existe no TraceLab.</p><button className="button button-primary" onClick={() => navigate("/")}>Voltar ao dashboard</button></div>;
}

export default App;
