import React from 'react'

interface LoadingButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean
  loadingText?: string
  children: React.ReactNode
}

const LoadingButton: React.FC<LoadingButtonProps> = ({
  loading = false,
  loadingText,
  children,
  disabled,
  ...props
}) => {
  const spinnerStyle: React.CSSProperties = {
    display: 'inline-block',
    width: '14px',
    height: '14px',
    border: '2px solid #ffffff',
    borderTop: '2px solid transparent',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
    marginRight: '8px',
    verticalAlign: 'middle',
  }

  return (
    <>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
      <button {...props} disabled={disabled || loading}>
        {loading && <span style={spinnerStyle} role="status" aria-label="Chargement" />}
        {loading ? (loadingText || 'Chargement...') : children}
      </button>
    </>
  )
}

export default LoadingButton
