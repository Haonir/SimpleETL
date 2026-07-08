import { describe, it, expect } from 'vitest'
import { logger } from '../logger'

describe('logger', () => {
  it('exports debug function', () => {
    expect(typeof logger.debug).toBe('function')
  })
  it('exports info function', () => {
    expect(typeof logger.info).toBe('function')
  })
  it('exports warn function', () => {
    expect(typeof logger.warn).toBe('function')
  })
  it('exports error function', () => {
    expect(typeof logger.error).toBe('function')
  })
  it('debug is callable without throwing', () => {
    expect(() => logger.debug('test')).not.toThrow()
  })
  it('info is callable without throwing', () => {
    expect(() => logger.info('test')).not.toThrow()
  })
  it('warn is callable without throwing', () => {
    expect(() => logger.warn('test')).not.toThrow()
  })
  it('error is callable without throwing', () => {
    expect(() => logger.error('test')).not.toThrow()
  })
})
