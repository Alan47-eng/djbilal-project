export function getApiErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (typeof item === 'string') return item;
      if (!item || typeof item !== 'object') return null;
      const message = typeof item.msg === 'string' ? item.msg : item.message;
      if (typeof message !== 'string') return null;
      const location = Array.isArray(item.loc)
        ? item.loc.filter((part) => part !== 'body').join('.')
        : '';
      return location ? `${location}: ${message}` : message;
    }).filter(Boolean);
    if (messages.length) return messages.join('; ');
  }

  if (detail && typeof detail === 'object') {
    const message = detail.message || detail.detail;
    if (typeof message === 'string' && message.trim()) return message;
  }

  return typeof error?.message === 'string' && error.message.trim()
    ? error.message
    : fallback;
}
