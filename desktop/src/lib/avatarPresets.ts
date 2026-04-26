export type AvatarPreset = {
  id: string
  name: string
  url: string
}

function svgDataUrl(svg: string): string {
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg.replace(/\s+/g, ' ').trim())}`
}

export const AVATAR_PRESETS: AvatarPreset[] = [
  {
    id: 'avatar-preset-1',
    name: '晨光',
    url: svgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="morning-bg" x1="14" y1="8" x2="84" y2="90" gradientUnits="userSpaceOnUse">
            <stop stop-color="#fff2d8"/>
            <stop offset="0.58" stop-color="#f6d7bc"/>
            <stop offset="1" stop-color="#d7edf0"/>
          </linearGradient>
          <linearGradient id="morning-hair" x1="25" y1="16" x2="72" y2="70" gradientUnits="userSpaceOnUse">
            <stop stop-color="#594135"/>
            <stop offset="1" stop-color="#221a20"/>
          </linearGradient>
        </defs>
        <rect width="96" height="96" rx="26" fill="url(#morning-bg)"/>
        <circle cx="78" cy="20" r="12" fill="#fff8e7" opacity="0.74"/>
        <path d="M14 70c15 7 34 7 58-3 7-3 12-2 16 3v26H14Z" fill="#9fc7bc" opacity="0.42"/>
        <path d="M30 82c3-17 13-28 28-28 14 0 24 10 28 28Z" fill="#355e65"/>
        <path d="M28 36c1-14 12-25 27-25 12 0 23 7 27 19 5 15-4 32-9 39-5-9-9-19-9-32-9 5-22 6-36-1Z" fill="url(#morning-hair)"/>
        <path d="M35 31c-3 8-3 19 1 29 4 8 12 12 20 11 11-1 17-8 19-20 1-7 0-14-4-19-8 6-22 8-36-1Z" fill="#f3cdbb"/>
        <path d="M35 48c-6-1-8 8-2 11 2 1 4 1 5 0" fill="#f3cdbb"/>
        <path d="M42 46c3-2 6-2 9 0" stroke="#2d2327" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M60 46c3-2 6-2 9 0" stroke="#2d2327" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M51 57c4 3 9 3 14-1" stroke="#7e4a44" stroke-width="2.3" stroke-linecap="round" fill="none"/>
        <circle cx="43" cy="54" r="3.5" fill="#df8d83" opacity="0.35"/>
        <circle cx="69" cy="52" r="3" fill="#df8d83" opacity="0.28"/>
        <path d="M32 82c7 5 20 7 32 5 6-1 13-3 19-6v15H32Z" fill="#f8f1dc" opacity="0.28"/>
      </svg>
    `),
  },
  {
    id: 'avatar-preset-2',
    name: '青岚',
    url: svgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="moss-bg" x1="12" y1="12" x2="84" y2="88" gradientUnits="userSpaceOnUse">
            <stop stop-color="#dff7ee"/>
            <stop offset="0.52" stop-color="#8fc9bd"/>
            <stop offset="1" stop-color="#27475a"/>
          </linearGradient>
          <linearGradient id="moss-shirt" x1="23" y1="60" x2="84" y2="96" gradientUnits="userSpaceOnUse">
            <stop stop-color="#f5efe5"/>
            <stop offset="1" stop-color="#24606c"/>
          </linearGradient>
        </defs>
        <rect width="96" height="96" rx="26" fill="url(#moss-bg)"/>
        <path d="M10 29c18-9 43-14 72-5" stroke="#f7fff8" stroke-width="10" stroke-linecap="round" opacity="0.26"/>
        <path d="M14 78c10-13 21-20 34-20 16 0 27 8 36 24v14H14Z" fill="url(#moss-shirt)"/>
        <path d="M30 39c0-16 12-27 29-25 13 1 22 11 21 25-1 18-11 31-27 31-15 0-23-12-23-31Z" fill="#18333e"/>
        <path d="M34 41c2-12 11-19 24-18 11 1 18 8 18 20 0 14-8 25-22 26-12 1-20-10-20-28Z" fill="#efd1bf"/>
        <path d="M31 37c6-16 20-25 38-18 9 4 13 12 13 24-11-8-24-14-51-6Z" fill="#1f4a4b"/>
        <path d="M48 42c-4-2-7-2-11 0" stroke="#18333e" stroke-width="2.1" stroke-linecap="round"/>
        <path d="M65 42c4-2 7-2 10 0" stroke="#18333e" stroke-width="2.1" stroke-linecap="round"/>
        <path d="M39 49h11c2 0 3 1 3 3s-1 3-3 3H39c-2 0-3-1-3-3s1-3 3-3Zm21 0h11c2 0 3 1 3 3s-1 3-3 3H60c-2 0-3-1-3-3s1-3 3-3Z" fill="none" stroke="#315063" stroke-width="1.8"/>
        <path d="M53 52h4" stroke="#315063" stroke-width="1.8" stroke-linecap="round"/>
        <path d="M49 60c5 2 11 2 15-1" stroke="#754e47" stroke-width="2.1" stroke-linecap="round" fill="none"/>
        <path d="M25 81c9-7 21-10 36-8 8 1 15 4 21 8v15H25Z" fill="#0f313b" opacity="0.42"/>
      </svg>
    `),
  },
  {
    id: 'avatar-preset-3',
    name: '桃雾',
    url: svgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-hidden="true">
        <defs>
          <radialGradient id="peach-bg" cx="32" cy="22" r="78" gradientUnits="userSpaceOnUse">
            <stop stop-color="#fff8ea"/>
            <stop offset="0.55" stop-color="#ffd1d7"/>
            <stop offset="1" stop-color="#bfa8ef"/>
          </radialGradient>
          <linearGradient id="peach-hair" x1="20" y1="16" x2="80" y2="84" gradientUnits="userSpaceOnUse">
            <stop stop-color="#f4f0ec"/>
            <stop offset="0.42" stop-color="#d9d4d5"/>
            <stop offset="1" stop-color="#8d8493"/>
          </linearGradient>
        </defs>
        <rect width="96" height="96" rx="26" fill="url(#peach-bg)"/>
        <path d="M9 64c22-12 47-13 78-3" stroke="#fff7f8" stroke-width="14" stroke-linecap="round" opacity="0.25"/>
        <path d="M18 90c5-20 19-33 34-33 17 0 30 13 35 33Z" fill="#8d78bc"/>
        <path d="M25 43c-2-19 10-32 29-32 17 0 27 12 27 29 0 27-17 39-31 39-17 0-24-18-25-36Z" fill="url(#peach-hair)"/>
        <path d="M32 38c2-13 10-19 22-19 13 0 20 8 21 22 1 17-8 28-23 28-12 0-20-11-20-31Z" fill="#f1c9b4"/>
        <path d="M28 38c11 0 23-5 30-17 7 11 13 17 22 18-2-17-12-28-27-29-16-1-27 10-25 28Z" fill="#f6f1ee"/>
        <circle cx="43" cy="46" r="2.6" fill="#45333a"/>
        <circle cx="62" cy="46" r="2.6" fill="#45333a"/>
        <path d="M42 42c4-3 8-3 11 0" stroke="#5a4850" stroke-width="2" stroke-linecap="round"/>
        <path d="M59 42c4-3 8-3 11 0" stroke="#5a4850" stroke-width="2" stroke-linecap="round"/>
        <path d="M47 57c5 3 11 3 16-1" stroke="#a26064" stroke-width="2.2" stroke-linecap="round" fill="none"/>
        <circle cx="37" cy="55" r="4.5" fill="#f0a2a8" opacity="0.36"/>
        <circle cx="68" cy="54" r="4" fill="#f0a2a8" opacity="0.3"/>
        <path d="M30 81c12 6 32 6 47-1v16H30Z" fill="#ffe6d4" opacity="0.22"/>
      </svg>
    `),
  },
  {
    id: 'avatar-preset-4',
    name: '夜航',
    url: svgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="night-bg" x1="9" y1="8" x2="86" y2="90" gradientUnits="userSpaceOnUse">
            <stop stop-color="#516b9f"/>
            <stop offset="0.48" stop-color="#202f57"/>
            <stop offset="1" stop-color="#0f172f"/>
          </linearGradient>
          <linearGradient id="night-hood" x1="20" y1="14" x2="79" y2="91" gradientUnits="userSpaceOnUse">
            <stop stop-color="#243f6a"/>
            <stop offset="1" stop-color="#07101f"/>
          </linearGradient>
        </defs>
        <rect width="96" height="96" rx="26" fill="url(#night-bg)"/>
        <circle cx="22" cy="20" r="3" fill="#e8f2ff" opacity="0.65"/>
        <circle cx="74" cy="28" r="2" fill="#e8f2ff" opacity="0.45"/>
        <path d="M17 90c5-28 17-48 35-55 19 6 31 25 35 55Z" fill="url(#night-hood)"/>
        <path d="M28 79c1-28 11-53 28-57 15 7 25 27 25 57-8-7-18-10-28-10-9 0-17 3-25 10Z" fill="#142642"/>
        <path d="M38 45c1-13 9-21 20-21 12 0 20 9 20 23 0 14-8 23-21 23-12 0-19-10-19-25Z" fill="#e8c5b6"/>
        <path d="M34 43c5-17 17-26 32-22 9 2 15 9 17 20-13-3-26-2-49 2Z" fill="#0e1b31"/>
        <path d="M50 44c-3-2-6-2-10 1" stroke="#1d2534" stroke-width="2.1" stroke-linecap="round"/>
        <path d="M66 43c4-2 7-1 10 1" stroke="#1d2534" stroke-width="2.1" stroke-linecap="round"/>
        <circle cx="45" cy="50" r="2.2" fill="#151d2a"/>
        <circle cx="70" cy="50" r="2.2" fill="#151d2a"/>
        <path d="M54 61c4 2 9 2 13-1" stroke="#6c4444" stroke-width="2.1" stroke-linecap="round" fill="none"/>
        <path d="M31 81c14-8 33-10 53-2v17H31Z" fill="#345376" opacity="0.36"/>
      </svg>
    `),
  },
  {
    id: 'avatar-preset-5',
    name: '橙野',
    url: svgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="ember-bg" x1="15" y1="10" x2="82" y2="90" gradientUnits="userSpaceOnUse">
            <stop stop-color="#ffe2b7"/>
            <stop offset="0.5" stop-color="#ef9b62"/>
            <stop offset="1" stop-color="#7a5e6d"/>
          </linearGradient>
          <linearGradient id="ember-curls" x1="20" y1="16" x2="78" y2="74" gradientUnits="userSpaceOnUse">
            <stop stop-color="#b76034"/>
            <stop offset="1" stop-color="#4c261d"/>
          </linearGradient>
        </defs>
        <rect width="96" height="96" rx="26" fill="url(#ember-bg)"/>
        <path d="M9 27c21 10 43 9 77-6" stroke="#fff0d2" stroke-width="13" stroke-linecap="round" opacity="0.24"/>
        <path d="M20 88c4-17 16-29 32-31 17 1 29 13 34 31Z" fill="#70496a"/>
        <circle cx="37" cy="33" r="13" fill="url(#ember-curls)"/>
        <circle cx="56" cy="27" r="15" fill="url(#ember-curls)"/>
        <circle cx="68" cy="42" r="15" fill="url(#ember-curls)"/>
        <circle cx="31" cy="48" r="12" fill="url(#ember-curls)"/>
        <path d="M34 39c2-12 10-18 22-18 13 0 21 8 23 21 2 16-8 28-24 29-13 0-21-11-21-32Z" fill="#efc7ad"/>
        <path d="M31 42c10-3 20-9 28-19 4 8 11 14 21 17-2-16-12-26-27-27-15 0-24 10-22 29Z" fill="#8b4428"/>
        <circle cx="44" cy="48" r="2.4" fill="#2e2020"/>
        <circle cx="65" cy="47" r="2.4" fill="#2e2020"/>
        <path d="M48 60c5 4 12 3 17-1" stroke="#7e463e" stroke-width="2.2" stroke-linecap="round" fill="none"/>
        <circle cx="41" cy="56" r="1.2" fill="#a76552"/>
        <circle cx="47" cy="55" r="1.1" fill="#a76552"/>
        <circle cx="62" cy="54" r="1.2" fill="#a76552"/>
        <path d="M27 85c9 4 20 6 32 5 10 0 20-3 27-7v13H27Z" fill="#ffcf91" opacity="0.24"/>
      </svg>
    `),
  },
  {
    id: 'avatar-preset-6',
    name: '月白',
    url: svgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="lilac-bg" x1="12" y1="9" x2="87" y2="91" gradientUnits="userSpaceOnUse">
            <stop stop-color="#f3f0ff"/>
            <stop offset="0.54" stop-color="#c9bfdc"/>
            <stop offset="1" stop-color="#55556d"/>
          </linearGradient>
          <linearGradient id="lilac-hair" x1="26" y1="13" x2="75" y2="70" gradientUnits="userSpaceOnUse">
            <stop stop-color="#d9c9ee"/>
            <stop offset="1" stop-color="#5d5874"/>
          </linearGradient>
        </defs>
        <rect width="96" height="96" rx="26" fill="url(#lilac-bg)"/>
        <circle cx="76" cy="18" r="13" fill="#fff" opacity="0.33"/>
        <path d="M16 88c5-18 17-29 35-29 16 0 28 11 33 29Z" fill="#3b4055"/>
        <path d="M30 38c0-15 11-27 27-27 14 0 23 10 24 24 1 23-11 39-29 39-14 0-22-12-22-36Z" fill="url(#lilac-hair)"/>
        <path d="M36 39c2-12 10-19 22-19 11 0 18 8 18 20 1 17-8 29-22 29-12 0-19-11-18-30Z" fill="#ead0c3"/>
        <path d="M31 39c10 1 25-4 38-17 7 6 11 15 12 27 3-17-6-34-24-37-17-2-28 9-26 27Z" fill="#9d8bc0"/>
        <path d="M43 44c3-2 7-2 10 0" stroke="#2d2f3d" stroke-width="2.1" stroke-linecap="round"/>
        <path d="M63 44c3-2 7-2 10 0" stroke="#2d2f3d" stroke-width="2.1" stroke-linecap="round"/>
        <path d="M50 58c4 2 9 2 13-1" stroke="#76535f" stroke-width="2.1" stroke-linecap="round" fill="none"/>
        <circle cx="77" cy="51" r="3.4" fill="#d7d0ef"/>
        <circle cx="78" cy="51" r="1.6" fill="#73658c"/>
        <path d="M24 84c16 7 35 8 58-2v14H24Z" fill="#f7f0ff" opacity="0.2"/>
      </svg>
    `),
  },
  {
    id: 'avatar-preset-7',
    name: '海玻璃',
    url: svgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="tide-bg" x1="10" y1="8" x2="86" y2="88" gradientUnits="userSpaceOnUse">
            <stop stop-color="#dcfff9"/>
            <stop offset="0.48" stop-color="#8ad9d6"/>
            <stop offset="1" stop-color="#326d7e"/>
          </linearGradient>
          <linearGradient id="tide-hair" x1="24" y1="18" x2="77" y2="77" gradientUnits="userSpaceOnUse">
            <stop stop-color="#193340"/>
            <stop offset="1" stop-color="#0a171d"/>
          </linearGradient>
        </defs>
        <rect width="96" height="96" rx="26" fill="url(#tide-bg)"/>
        <path d="M8 72c18-9 35-9 54-1 11 5 19 4 27-2v27H8Z" fill="#d8fffa" opacity="0.26"/>
        <path d="M19 89c5-18 17-31 35-32 17 1 29 13 33 32Z" fill="#1d5a66"/>
        <path d="M27 38c1-16 13-27 30-26 16 1 26 12 25 29-1 21-12 36-29 36-16 0-27-14-26-39Z" fill="url(#tide-hair)"/>
        <path d="M34 39c1-12 9-19 22-19 12 0 20 8 21 21 1 17-9 28-23 28-13 0-21-11-20-30Z" fill="#efccb9"/>
        <path d="M28 40c10-1 27-8 38-20 10 8 15 18 14 30 4-17-5-35-24-37-18-1-29 10-28 27Z" fill="#16323d"/>
        <path d="M41 44c3-2 7-2 10 0" stroke="#18313a" stroke-width="2.1" stroke-linecap="round"/>
        <path d="M61 44c4-2 7-2 10 0" stroke="#18313a" stroke-width="2.1" stroke-linecap="round"/>
        <path d="M48 58c5 3 11 3 16-1" stroke="#77504e" stroke-width="2.2" stroke-linecap="round" fill="none"/>
        <path d="M70 25l8 2-1 8-8-2Z" fill="#b7fff0" opacity="0.78"/>
        <path d="M22 84c9 5 22 7 36 6 11-1 21-4 29-9v15H22Z" fill="#b9ece6" opacity="0.22"/>
      </svg>
    `),
  },
  {
    id: 'avatar-preset-8',
    name: '砂岩',
    url: svgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-hidden="true">
        <defs>
          <linearGradient id="sand-bg" x1="13" y1="8" x2="86" y2="89" gradientUnits="userSpaceOnUse">
            <stop stop-color="#f7ead1"/>
            <stop offset="0.5" stop-color="#d3b98f"/>
            <stop offset="1" stop-color="#5e7286"/>
          </linearGradient>
          <linearGradient id="sand-hair" x1="22" y1="12" x2="77" y2="65" gradientUnits="userSpaceOnUse">
            <stop stop-color="#d8b274"/>
            <stop offset="1" stop-color="#6e4d32"/>
          </linearGradient>
        </defs>
        <rect width="96" height="96" rx="26" fill="url(#sand-bg)"/>
        <path d="M13 33c16-11 40-16 69-9" stroke="#fff4df" stroke-width="12" stroke-linecap="round" opacity="0.26"/>
        <path d="M18 88c5-18 17-30 34-31 18 1 31 13 36 31Z" fill="#536b7d"/>
        <path d="M28 40c0-15 10-27 27-28 15 0 26 10 27 25 2 21-9 36-27 37-17 0-27-14-27-34Z" fill="url(#sand-hair)"/>
        <path d="M34 41c2-12 10-19 22-20 12 0 20 8 21 20 2 17-8 29-23 29-13 0-21-11-20-29Z" fill="#edc9ac"/>
        <path d="M29 39c9-5 19-12 24-22 8 8 17 13 29 17-4-15-14-24-28-24-15 1-25 11-25 29Z" fill="#b07a3e"/>
        <path d="M43 44c3-2 7-2 10 0" stroke="#352822" stroke-width="2.1" stroke-linecap="round"/>
        <path d="M62 44c4-2 7-2 10 0" stroke="#352822" stroke-width="2.1" stroke-linecap="round"/>
        <circle cx="45" cy="50" r="2.3" fill="#352822"/>
        <circle cx="67" cy="50" r="2.3" fill="#352822"/>
        <path d="M50 60c4 2 9 2 14-1" stroke="#83534a" stroke-width="2.2" stroke-linecap="round" fill="none"/>
        <circle cx="42" cy="55" r="1.1" fill="#a56f5c"/>
        <circle cx="48" cy="54" r="1" fill="#a56f5c"/>
        <circle cx="65" cy="55" r="1" fill="#a56f5c"/>
        <path d="M26 84c14 7 35 7 61-3v15H26Z" fill="#fff1d0" opacity="0.2"/>
      </svg>
    `),
  },
]

export const DEFAULT_SELF_AVATAR_URL = AVATAR_PRESETS[0].url
export const DEFAULT_OTHER_AVATAR_URL = AVATAR_PRESETS[1].url
