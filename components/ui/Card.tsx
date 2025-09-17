import { HTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outlined' | 'elevated'
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    return (
      <div
        className={clsx(
          'rounded-xl p-6',
          {
            'bg-white border border-gray-200': variant === 'default',
            'bg-white border-2 border-gray-300': variant === 'outlined',
            'bg-white shadow-lg border border-gray-200': variant === 'elevated',
          },
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)

Card.displayName = 'Card'
