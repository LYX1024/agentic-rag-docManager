type ToastType = 'success' | 'error' | 'warning' | 'info'

const colorMap: Record<ToastType, { bg: string; text: string; border: string }> = {
  success: { bg: '#000', text: '#fff', border: '#000' },
  error: { bg: '#ff006e', text: '#fff', border: '#ff006e' },
  warning: { bg: '#fff', text: '#000', border: '#000' },
  info: { bg: '#fff', text: '#000', border: '#000' }
}

export function showToast(message: string, type: ToastType = 'info') {
  const colors = colorMap[type]
  const toast = document.createElement('div')
  toast.textContent = message
  Object.assign(toast.style, {
    position: 'fixed',
    top: '20px',
    left: '50%',
    transform: 'translateX(-50%)',
    padding: '10px 24px',
    backgroundColor: colors.bg,
    color: colors.text,
    border: `2px solid ${colors.border}`,
    fontFamily: "'Courier New', Courier, monospace",
    fontSize: '14px',
    zIndex: '10000',
    boxShadow: '4px 4px 0px 0px rgba(0,0,0,1)',
    transition: 'opacity 0.3s ease',
    opacity: '1'
  })
  document.body.appendChild(toast)
  setTimeout(() => {
    toast.style.opacity = '0'
    setTimeout(() => {
      if (toast.parentNode) {
        document.body.removeChild(toast)
      }
    }, 300)
  }, 2500)
}

export const Toast = {
  success: (msg: string) => showToast(msg, 'success'),
  error: (msg: string) => showToast(msg, 'error'),
  warning: (msg: string) => showToast(msg, 'warning'),
  info: (msg: string) => showToast(msg, 'info')
}
