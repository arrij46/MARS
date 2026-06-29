// src/components/ClusterColumn.jsx
import React from "react";

export const ClusterColumn = ({ title, color, requirements, delay = 0 }) => {
  return (
    <div
      className="p-6 rounded-xl bg-card shadow-[var(--shadow-card)] animate-fade-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div
        className="w-12 h-12 rounded-full mx-auto mb-4"
        style={{ backgroundColor: color }}
      />
      <h3 className="font-semibold text-lg mb-3 text-center">{title}</h3>
      <ul className="space-y-2 text-sm text-muted-foreground">
        {requirements.map((req, i) => (
          <li key={i} className="p-3 rounded-lg bg-background border border-muted">
            {req}
          </li>
        ))}
      </ul>
    </div>
  );
};
