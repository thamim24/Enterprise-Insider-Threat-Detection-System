import clsx from 'clsx';
import { AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react';

const RISK_CONFIG = {
  CRITICAL: {
    bg: 'bg-red-100',
    text: 'text-red-700',
    border: 'border-red-200',
    icon: AlertTriangle,
  },
  HIGH: {
    bg: 'bg-orange-100',
    text: 'text-orange-700',
    border: 'border-orange-200',
    icon: AlertCircle,
  },
  MEDIUM: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-700',
    border: 'border-yellow-200',
    icon: Info,
  },
  LOW: {
    bg: 'bg-green-100',
    text: 'text-green-700',
    border: 'border-green-200',
    icon: CheckCircle,
  },
};

function RiskBadge({ level, size = 'md', showIcon = true }) {
  const config = RISK_CONFIG[level] || RISK_CONFIG.LOW;
  const Icon = config.icon;

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full border',
        config.bg,
        config.text,
        config.border,
        sizes[size]
      )}
    >
      {showIcon && <Icon className={clsx(iconSizes[size], 'mr-1')} />}
      {level}
    </span>
  );
}

export default RiskBadge;
