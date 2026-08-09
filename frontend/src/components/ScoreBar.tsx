interface ScoreBarProps {
  label: string;
  value: number;
  max: number;
  variant?: "default" | "defending";
}

export function ScoreBar({ label, value, max, variant = "default" }: ScoreBarProps) {
  const pct = Math.min(100, Math.round((value / max) * 100));

  return (
    <div className="score-bar-row">
      <div className="lbl">
        <span>{label}</span>
        <span>
          {value} / {max}
        </span>
      </div>
      <div className="score-bar-track">
        <div
          className={`score-bar-fill${variant === "defending" ? " def" : ""}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
