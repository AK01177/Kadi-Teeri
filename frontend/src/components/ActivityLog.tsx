interface ActivityLogProps {
  log: string[];
}

export function ActivityLog({ log }: ActivityLogProps) {
  const recent = log.slice(-10);

  return (
    <details className="log-details">
      <summary>Recent activity</summary>
      <div className="log-box">
        {recent.map((entry, i) => (
          <div key={i}>{entry}</div>
        ))}
      </div>
    </details>
  );
}
