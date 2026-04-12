export type AvatarPreset = {
  id: string
  name: string
  url: string
}

function svgDataUrl(svg: string): string {
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}

function buildAvatarSvg(config: {
  background: string
  hair: string
  shirt: string
  accent: string
  eye: string
  face: string
}): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-hidden="true">
  <rect width="96" height="96" rx="28" fill="${config.background}"/>
  <circle cx="48" cy="38" r="18" fill="${config.face}"/>
  <path d="M26 78c4-16 18-24 22-24s18 8 22 24" fill="${config.shirt}"/>
  <path d="M28 34c2-14 12-22 20-22 11 0 19 7 20 22-8-6-13-8-20-8s-12 2-20 8Z" fill="${config.hair}"/>
  <circle cx="41" cy="39" r="2.5" fill="${config.eye}"/>
  <circle cx="55" cy="39" r="2.5" fill="${config.eye}"/>
  <path d="M42 48c2 2 4 3 6 3s4-1 6-3" stroke="${config.eye}" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <circle cx="73" cy="23" r="9" fill="${config.accent}" opacity="0.9"/>
  <circle cx="22" cy="76" r="7" fill="${config.accent}" opacity="0.65"/>
</svg>`
}

export const AVATAR_PRESETS: AvatarPreset[] = [
  {
    id: 'avatar-preset-1',
    name: '晨雾',
    url: svgDataUrl(
      buildAvatarSvg({
        background: '#E9F4FF',
        hair: '#3B4A6B',
        shirt: '#6E8CE3',
        accent: '#9ED4FF',
        eye: '#25324B',
        face: '#F7D7C2',
      }),
    ),
  },
  {
    id: 'avatar-preset-2',
    name: '栀子',
    url: svgDataUrl(
      buildAvatarSvg({
        background: '#FFF2E8',
        hair: '#5C3A2E',
        shirt: '#F08F5A',
        accent: '#FFD08A',
        eye: '#40231B',
        face: '#F6D0B9',
      }),
    ),
  },
  {
    id: 'avatar-preset-3',
    name: '青柚',
    url: svgDataUrl(
      buildAvatarSvg({
        background: '#E8FFF4',
        hair: '#2E5A48',
        shirt: '#58B58C',
        accent: '#9DE0BF',
        eye: '#1F4033',
        face: '#F4D8C4',
      }),
    ),
  },
  {
    id: 'avatar-preset-4',
    name: '晚樱',
    url: svgDataUrl(
      buildAvatarSvg({
        background: '#FFF0F6',
        hair: '#53305E',
        shirt: '#D97DB0',
        accent: '#F7B6D8',
        eye: '#35203A',
        face: '#F6D7C7',
      }),
    ),
  },
  {
    id: 'avatar-preset-5',
    name: '海盐',
    url: svgDataUrl(
      buildAvatarSvg({
        background: '#EEF7F7',
        hair: '#2D4D57',
        shirt: '#4FA8B8',
        accent: '#8FD7E3',
        eye: '#1F3941',
        face: '#F5D9C6',
      }),
    ),
  },
]

export const DEFAULT_SELF_AVATAR_URL = AVATAR_PRESETS[0].url
export const DEFAULT_OTHER_AVATAR_URL = AVATAR_PRESETS[1].url
