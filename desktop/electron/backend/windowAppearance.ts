type WindowAppearanceOptions = {
  frame: boolean
  titleBarStyle: 'hidden'
  backgroundColor: string
  roundedCorners: boolean
}

type WindowAppearanceInput = {
  platform: NodeJS.Platform
  release: string
}

const NON_WINDOWS_APPEARANCE: WindowAppearanceOptions = {
  frame: false,
  titleBarStyle: 'hidden',
  backgroundColor: '#f5f5f5',
  roundedCorners: false,
}

const WINDOWS_10_APPEARANCE: WindowAppearanceOptions = {
  frame: false,
  titleBarStyle: 'hidden',
  backgroundColor: '#f3f3f3',
  roundedCorners: false,
}

const WINDOWS_11_APPEARANCE: WindowAppearanceOptions = {
  frame: false,
  titleBarStyle: 'hidden',
  backgroundColor: '#00000000',
  roundedCorners: true,
}

function getWindowsBuildNumber(release: string): number {
  const buildSegment = release.split('.').at(-1)
  return Number.parseInt(buildSegment ?? '', 10)
}

export function getWindowsAppearanceOptions(input: WindowAppearanceInput): WindowAppearanceOptions {
  if (input.platform !== 'win32') {
    return NON_WINDOWS_APPEARANCE
  }

  return getWindowsBuildNumber(input.release) >= 22000
    ? WINDOWS_11_APPEARANCE
    : WINDOWS_10_APPEARANCE
}
