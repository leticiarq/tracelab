import type { ReactNode, SVGProps } from "react";

import type { LabStatus } from "./types";
import { STATUS_LABELS } from "./types";

type IconProps = SVGProps<SVGSVGElement>;

function Icon({ children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true" {...props}>
      {children}
    </svg>
  );
}

export const Icons = {
  grid: (props: IconProps) => <Icon {...props}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></Icon>,
  flask: (props: IconProps) => <Icon {...props}><path d="M9 3h6M10 3v6l-5.5 9.2A1.8 1.8 0 0 0 6 21h12a1.8 1.8 0 0 0 1.5-2.8L14 9V3" /><path d="M7.5 15h9" /></Icon>,
  plus: (props: IconProps) => <Icon {...props}><path d="M12 5v14M5 12h14" /></Icon>,
  search: (props: IconProps) => <Icon {...props}><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></Icon>,
  edit: (props: IconProps) => <Icon {...props}><path d="m14 5 5 5M4 20l3.5-.7L19 7.8a2.1 2.1 0 0 0-3-3L4.7 16.3 4 20Z" /></Icon>,
  trash: (props: IconProps) => <Icon {...props}><path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6" /></Icon>,
  arrow: (props: IconProps) => <Icon {...props}><path d="m9 18 6-6-6-6" /></Icon>,
  menu: (props: IconProps) => <Icon {...props}><path d="M4 7h16M4 12h16M4 17h16" /></Icon>,
  close: (props: IconProps) => <Icon {...props}><path d="m6 6 12 12M18 6 6 18" /></Icon>,
  external: (props: IconProps) => <Icon {...props}><path d="M14 4h6v6M20 4 10 14" /><path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" /></Icon>,
  alert: (props: IconProps) => <Icon {...props}><path d="M12 3 2.8 19a1.3 1.3 0 0 0 1.1 2h16.2a1.3 1.3 0 0 0 1.1-2L12 3Z" /><path d="M12 9v5M12 18h.01" /></Icon>,
  check: (props: IconProps) => <Icon {...props}><path d="m5 12 4 4L19 6" /></Icon>,
  note: (props: IconProps) => <Icon {...props}><path d="M6 3h9l4 4v14H6V3Z" /><path d="M14 3v5h5M9 12h6M9 16h6" /></Icon>,
  settings: (props: IconProps) => <Icon {...props}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V21h-4v-.08A1.7 1.7 0 0 0 8.94 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.57 15 1.7 1.7 0 0 0 3 14H3v-4h.08A1.7 1.7 0 0 0 4.6 8.94a1.7 1.7 0 0 0-.34-1.88L4.2 7l2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.57 1.7 1.7 0 0 0 10 3h4v.08A1.7 1.7 0 0 0 15.06 4.6a1.7 1.7 0 0 0 1.88-.34L17 4.2 19.8 7l-.06.06A1.7 1.7 0 0 0 19.4 9 1.7 1.7 0 0 0 21 10h.08v4H21a1.7 1.7 0 0 0-1.6 1Z" /></Icon>,
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  return <button className={`button button-${variant} ${className}`} {...props} />;
}

export function StatusBadge({ status }: { status: LabStatus }) {
  return <span className={`status status-${status}`}><span aria-hidden="true" />{STATUS_LABELS[status]}</span>;
}

export function LoadingState({ label = "Carregando dados" }: { label?: string }) {
  return <div className="state-panel" role="status"><span className="spinner" /><p>{label}…</p></div>;
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="state-panel state-error" role="alert">
      <Icons.alert className="h-7 w-7" />
      <div><strong>Algo não saiu como esperado</strong><p>{message}</p></div>
      {retry && <Button variant="secondary" onClick={retry}>Tentar novamente</Button>}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon ?? <Icons.flask className="h-7 w-7" />}</div>
      <h3>{title}</h3><p>{description}</p>{action}
    </div>
  );
}

export function Toast({ message, tone = "success" }: { message: string; tone?: "success" | "error" }) {
  return <div className={`toast toast-${tone}`} role={tone === "error" ? "alert" : "status"}>{tone === "success" ? <Icons.check className="h-5 w-5" /> : <Icons.alert className="h-5 w-5" />}{message}</div>;
}

export function ConfirmDialog({
  title,
  description,
  confirmLabel,
  busy,
  onConfirm,
  onCancel,
}: {
  title: string;
  description: string;
  confirmLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onCancel()}>
      <section className="dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title">
        <div className="dialog-danger"><Icons.alert className="h-6 w-6" /></div>
        <h2 id="confirm-title">{title}</h2><p>{description}</p>
        <div className="dialog-actions"><Button variant="secondary" onClick={onCancel} disabled={busy}>Cancelar</Button><Button variant="danger" onClick={onConfirm} disabled={busy}>{busy ? "Excluindo…" : confirmLabel}</Button></div>
      </section>
    </div>
  );
}
