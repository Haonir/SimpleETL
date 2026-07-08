type LogLevel = 'debug' | 'info' | 'warn' | 'error'

const PREFIX = '[SimpleETL]'

function shouldLog(level: LogLevel): boolean {
  if (import.meta.env.DEV) return true
  return level === 'warn' || level === 'error'
}

export const logger = {
  debug: (...args: unknown[]) => {
    if (shouldLog('debug')) console.debug(PREFIX, ...args)
  },
  info: (...args: unknown[]) => {
    if (shouldLog('info')) console.info(PREFIX, ...args)
  },
  warn: (...args: unknown[]) => {
    if (shouldLog('warn')) console.warn(PREFIX, ...args)
  },
  error: (...args: unknown[]) => {
    if (shouldLog('error')) console.error(PREFIX, ...args)
  }
}
