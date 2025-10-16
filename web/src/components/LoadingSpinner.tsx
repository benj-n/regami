import React from 'react'

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large'
  text?: string
  fullPage?: boolean
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  text,
  fullPage = false
}) => {
  const sizeMap = {
    small: 20,
    medium: 40,
    large: 60,
  }

  const spinnerSize = sizeMap[size]

  const spinnerStyle: React.CSSProperties = {
    border: `${spinnerSize / 10}px solid #f3f3f3`,
    borderTop: `${spinnerSize / 10}px solid #3498db`,
    borderRadius: '50%',
    width: spinnerSize,
    height: spinnerSize,
    animation: 'spin 1s linear infinite',
  }

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    ...(fullPage ? {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      zIndex: 9999,
    } : {
      padding: '20px',
    }),
  }

  return (
    <>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
      <div style={containerStyle}>
        <div style={spinnerStyle} role="status" aria-label="Chargement en cours" />
        {text && <p style={{ margin: 0, color: '#666' }}>{text}</p>}
      </div>
    </>
  )
}

export default LoadingSpinner
