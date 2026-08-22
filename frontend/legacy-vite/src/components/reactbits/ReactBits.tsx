import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";

type ChildrenProps = {
  children: ReactNode;
  className?: string;
};

export function SoftAurora({ className = "" }: { className?: string }) {
  return (
    <div className={`rb-soft-aurora ${className}`} aria-hidden="true">
      <span />
      <span />
      <span />
    </div>
  );
}

export function BlurText({ children, className = "" }: ChildrenProps) {
  return <span className={`rb-blur-text ${className}`}>{children}</span>;
}

export function AnimatedContent({ children, className = "" }: ChildrenProps) {
  return <div className={`rb-animated-content ${className}`}>{children}</div>;
}

export function SpotlightCard({ children, className = "" }: ChildrenProps) {
  return <div className={`rb-spotlight-card ${className}`}>{children}</div>;
}

export function BorderGlow({ children, className = "", active = false }: ChildrenProps & { active?: boolean }) {
  return <div className={`rb-border-glow ${active ? "is-active" : ""} ${className}`}>{children}</div>;
}

export function ShinyText({ children, className = "" }: ChildrenProps) {
  return <span className={`rb-shiny-text ${className}`}>{children}</span>;
}

export function CountUp({ value, suffix = "", className = "" }: { value: number; suffix?: string; className?: string }) {
  return (
    <span className={`rb-count-up ${className}`} data-value={Math.round(value)}>
      {Math.round(value)}
      {suffix}
    </span>
  );
}

export function AnimatedList({ children, className = "" }: ChildrenProps) {
  return <div className={`rb-animated-list ${className}`}>{children}</div>;
}

export function MagicBento({ children, className = "" }: ChildrenProps) {
  return <div className={`rb-magic-bento ${className}`}>{children}</div>;
}

export function Stepper({
  steps,
  active,
  className = "",
}: {
  steps: string[];
  active: number;
  className?: string;
}) {
  return (
    <ol className={`rb-stepper ${className}`} aria-label="Analysis workflow">
      {steps.map((step, index) => (
        <li key={step} className={index <= active ? "active" : ""} aria-current={index === active ? "step" : undefined}>
          <span>{index + 1}</span>
          <strong>{step}</strong>
        </li>
      ))}
    </ol>
  );
}

export function PillNav({ className = "" }: { className?: string }) {
  const links = [
    { to: "/app", label: "Overview", end: true },
    { to: "/app/analyze", label: "Analyze" },
    { to: "/app/history", label: "History" },
    { to: "/app/settings", label: "Settings" },
  ];
  return (
    <nav className={`rb-pill-nav ${className}`} aria-label="Smart Cricket app navigation">
      {links.map((link) => (
        <NavLink key={link.to} to={link.to} end={link.end}>
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
