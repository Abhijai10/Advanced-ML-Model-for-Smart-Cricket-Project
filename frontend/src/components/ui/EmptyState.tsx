import React from 'react';

interface EmptyStateProps {
  icon: React.ReactNode;
  heading: string;
  description: string;
  action?: React.ReactNode;
}

export default function EmptyState({
  icon,
  heading,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4 text-accent">
        {icon}
      </div>
      <h3 className="text-base font-semibold text-foreground mb-2">{heading}</h3>
      <p className="text-sm text-muted-foreground max-w-xs mb-6">{description}</p>
      {action}
    </div>
  );
}