type ToastType = 'success' | 'error' | 'warning' | 'info'

const colorMap: Record<ToastType, { bg: string; text: string; border: string }> = {
  success: { bg: '#5a7a6b', text: '#f5f0eb', border: '#d4cdc5' },
  error: { bg: '#607683', text: '#f5f0eb', border: '#d4cdc5' },
  warning: { bg: '#c9a88c', text: '#3d3d3d', border: '#d4cdc5' },
  info: { bg: '#f5f0eb', text: '#3d3d3d', border: '#d4cdc5' }
}

export function showToast(message: string, type: ToastType = 'info') {
  const colors = colorMap[type]
  const toast = document.createElement('div')
  toast.textContent = message
  Object.assign(toast.style, {
    position: 'fixed',
    top: '24px',
    left: '50%',
    transform: 'translateX(-50%)',
    padding: '10px 28px',
    backgroundColor: colors.bg,
    color: colors.text,
    border: `1px solid ${colors.border}`,
    borderRadius: '2px',
    fontFamily: "'Courier New', Courier, monospace",
    fontSize: '13px',
    fontWeight: '300',
    letterSpacing: '0.025em',
    zIndex: '10000',
    boxShadow: '0 1px 4px rgba(61,61,61,0.05)',
    transition: 'opacity 0.7s ease-in-out',
    opacity: '1'
  })
  document.body.appendChild(toast)
  setTimeout(() => {
    toast.style.opacity = '0'
    setTimeout(() => {
      if (toast.parentNode) {
        document.body.removeChild(toast)
      }
    }, 700)
  }, 2500)
}

export const Toast = {
  success: (msg: string) => showToast(msg, 'success'),
  error: (msg: string) => showToast(msg, 'error'),
  warning: (msg: string) => showToast(msg, 'warning'),
  info: (msg: string) => showToast(msg, 'info')
}
