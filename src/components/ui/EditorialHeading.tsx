import { cn } from '../../lib/utils';
import type { ReactNode } from 'react';

interface EditorialHeadingProps {
  eyebrow?: string;
  children: ReactNode;
  align?: 'left' | 'center';
  size?: 'xl' | 'lg' | 'md';
  className?: string;
}

export default function EditorialHeading({ eyebrow, children, align = 'left', size = 'lg', className }: EditorialHeadingProps) {
  const sizes = {
    xl: 'text-[13vw] leading-[0.92] sm:text-[9vw] lg:text-[6.2vw]',
    lg: 'text-4xl leading-[1.02] sm:text-5xl lg:text-6xl',
    md: 'text-3xl leading-[1.05] sm:text-4xl',
  };

  return (
    <div className={cn(align === 'center' && 'text-center', className)}>
      {eyebrow && (
        <p className="mb-3 font-mono text-xs tracking-[0.25em] text-ink-3 uppercase">{eyebrow}</p>
      )}
      <h2 className={cn('font-serif font-medium tracking-tight text-ink text-balance', sizes[size])}>
        {children}
      </h2>
    </div>
  );
}
