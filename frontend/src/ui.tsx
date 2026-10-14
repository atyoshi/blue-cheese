import { useRef, type ReactNode } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import * as Tooltip from "@radix-ui/react-tooltip";
import {
  X,
  ArrowRight,
  Inbox,
  LoaderCircle,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { label } from "./api";

export function Hint({
  text,
  children,
}: {
  text: string;
  children: ReactNode;
}) {
  return (
    <Tooltip.Root delayDuration={350}>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          className="tooltip"
          sideOffset={7}
          collisionPadding={12}
        >
          {text}
          <Tooltip.Arrow className="tooltip-arrow" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
export function Badge({
  value,
  priority = false,
}: {
  value?: string;
  priority?: boolean;
}) {
  const v = (value || "unknown").toLowerCase();
  const tone = /failed|malicious|high|incident/.test(v)
    ? "danger"
    : /suspicious|medium|cancel|uncertain|insufficient|warning/.test(v)
      ? "warning"
      : /complete|benign|success|connected/.test(v)
        ? "success"
        : /running|investigating|queued|working/.test(v)
          ? "accent"
          : "neutral";
  return (
    <span className={"badge " + tone}>
      <span className="status-dot" />
      {label(value)}
      {priority ? " priority" : ""}
    </span>
  );
}
export function Empty({
  title,
  detail,
  children,
}: {
  title: string;
  detail?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Inbox size={24} />
      </div>
      <h2>{title}</h2>
      {detail && <p>{detail}</p>}
      {children}
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <LoaderCircle size={18} className="spin" /> Loading
    </div>
  );
}
export function ErrorNotice({
  message,
  retry,
}: {
  message?: string;
  retry?: () => void;
}) {
  return message ? (
    <div className="notice error" role="alert">
      <AlertCircle size={18} />
      <span>{message}</span>
      {retry && (
        <button className="text-button" onClick={retry}>
          Retry
        </button>
      )}
    </div>
  ) : null;
}
export function Pagination({
  page,
  total,
  size,
  onChange,
}: {
  page: number;
  total: number;
  size: number;
  onChange: (p: number) => void;
}) {
  return (
    <div className="pagination">
      <span>
        {total.toLocaleString()} records · Page {page} of{" "}
        {Math.max(1, Math.ceil(total / size))}
      </span>
      <div className="button-group">
        <button
          className="icon-button"
          aria-label="Previous page"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          <ChevronLeft />
        </button>
        <button
          className="icon-button"
          aria-label="Next page"
          disabled={page * size >= total}
          onClick={() => onChange(page + 1)}
        >
          <ChevronRight />
        </button>
      </div>
    </div>
  );
}
export function Drawer({
  open,
  onClose,
  title,
  description,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  const returnFocus = useRef<HTMLElement | null>(null);
  return (
    <Dialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content
          className={"drawer " + (wide ? "wide" : "")}
          onOpenAutoFocus={() => {
            returnFocus.current = document.activeElement as HTMLElement;
          }}
          onCloseAutoFocus={(e) => {
            e.preventDefault();
            const element = returnFocus.current?.isConnected
              ? returnFocus.current
              : document.getElementById("main");
            element?.focus();
          }}
        >
          <div className="drawer-heading">
            <div>
              <Dialog.Title>{title}</Dialog.Title>
              <Dialog.Description className={description ? "muted" : "sr-only"}>
                {description || title + " details"}
              </Dialog.Description>
            </div>
            <Dialog.Close className="icon-button" aria-label="Close panel">
              <X />
            </Dialog.Close>
          </div>
          <div className="drawer-body">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
export function Section({
  title,
  extra,
  children,
  className = "",
}: {
  title: string;
  extra?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={"panel " + className}>
      <div className="section-heading">
        <h2>{title}</h2>
        {extra}
      </div>
      {children}
    </section>
  );
}
export function ActionLink({
  children,
  onClick,
}: {
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button className="text-button" onClick={onClick}>
      {children}
      <ArrowRight size={15} />
    </button>
  );
}
export function Json({ value }: { value: unknown }) {
  return (
    <pre className="code">
      {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function tabKeys(
  event: React.KeyboardEvent,
  values: string[],
  selected: string,
  setSelected: (value: string) => void,
) {
  const index = values.indexOf(selected);
  const next =
    event.key === "ArrowRight"
      ? (index + 1) % values.length
      : event.key === "ArrowLeft"
        ? (index + values.length - 1) % values.length
        : event.key === "Home"
          ? 0
          : event.key === "End"
            ? values.length - 1
            : -1;
  if (next >= 0) {
    event.preventDefault();
    setSelected(values[next]);
    const tabs =
      event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>(
        '[role="tab"]',
      );
    tabs?.[next]?.focus();
  }
}

function Emphasis({ text }: { text: string }) {
  return (
    <>
      {text
        .split(/(\*\*[^*\n]+\*\*)/g)
        .map((part, i) =>
          part.startsWith("**") && part.endsWith("**") ? (
            <strong key={i}>{part.slice(2, -2)}</strong>
          ) : (
            part
          ),
        )}
    </>
  );
}

export function Prose({
  text = "",
  blocks,
}: {
  text?: string;
  blocks?: import("./api").PresentationBlock[];
}) {
  const parts =
    blocks ||
    text
      .split(/\n\s*\n/)
      .filter(Boolean)
      .map((part) => {
        const lines = part.split("\n").filter(Boolean);
        return {
          title: "",
          kind: lines.length > 1 ? "bullets" : "paragraph",
          items: lines.map((line) => line.replace(/^[-*]\s+/, "")),
        };
      });
  return (
    <div className="readable-prose">
      {parts.map((part, i) => (
        <div className="prose-block" key={i}>
          {part.title && <h3>{part.title}</h3>}
          {part.kind === "bullets" ? (
            <ul>
              {part.items.map((item, j) => (
                <li key={j}>
                  <Emphasis text={item} />
                </li>
              ))}
            </ul>
          ) : (
            part.items.map((item, j) => (
              <p key={j}>
                <Emphasis text={item} />
              </p>
            ))
          )}
        </div>
      ))}
    </div>
  );
}

export function Guidance() {
  return (
    <details className="shared-guidance">
      <summary>How to interpret findings</summary>
      <ul>
        <li>
          Alerts are sensor rule matches. Severity indicates review priority.
        </li>
        <li>
          Network records alone do not identify a process or establish
          authorization.
        </li>
        <li>
          Model findings require review; scores are not calibrated
          probabilities.
        </li>
        <li>
          Execution status describes work performed. Analyst decisions are
          recorded separately.
        </li>
      </ul>
    </details>
  );
}
