import { describe, expect, it } from 'vitest'
import { getWindowsAppearanceOptions } from '../electron/backend/windowAppearance.js'

describe('getWindowsAppearanceOptions', () => {
  it('returns Win11 appearance defaults for modern native chrome', () => {
    expect(
      getWindowsAppearanceOptions({
        platform: 'win32',
        release: '10.0.22631',
      }),
    ).toMatchObject({
      backgroundColor: '#00000000',
      roundedCorners: true,
      titleBarStyle: 'hidden',
      frame: false,
    })
  })

  it('falls back to square corners on Win10', () => {
    expect(
      getWindowsAppearanceOptions({
        platform: 'win32',
        release: '10.0.19045',
      }),
    ).toMatchObject({
      frame: false,
      titleBarStyle: 'hidden',
      backgroundColor: '#f3f3f3',
      roundedCorners: false,
    })
  })

  it('returns non-Windows defaults without modern Windows corners', () => {
    expect(
      getWindowsAppearanceOptions({
        platform: 'darwin',
        release: '23.6.0',
      }),
    ).toMatchObject({
      frame: false,
      titleBarStyle: 'hidden',
      backgroundColor: '#f5f5f5',
      roundedCorners: false,
    })
  })
})
