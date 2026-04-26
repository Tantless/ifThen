export type AvatarPreset = {
  id: string
  name: string
  url: string
}

function avatarAssetUrl(fileName: string): string {
  return `./avatars/${fileName}`
}

export const AVATAR_PRESETS: AvatarPreset[] = [
  { id: 'avatar-preset-1', name: '晴阳', url: avatarAssetUrl('01-mist-mountain.webp') },
  { id: 'avatar-preset-2', name: '紫雨', url: avatarAssetUrl('02-neon-rain.webp') },
  { id: 'avatar-preset-3', name: '珊海', url: avatarAssetUrl('03-coral-beach.webp') },
  { id: 'avatar-preset-4', name: '雪帽', url: avatarAssetUrl('04-snow-cabin.webp') },
  { id: 'avatar-preset-5', name: '熊绒', url: avatarAssetUrl('05-studio-amber.webp') },
  { id: 'avatar-preset-6', name: '青书', url: avatarAssetUrl('06-editorial-blue.webp') },
  { id: 'avatar-preset-7', name: '银星', url: avatarAssetUrl('07-street-silver.webp') },
  { id: 'avatar-preset-8', name: '窗影', url: avatarAssetUrl('08-vintage-window.webp') },
  { id: 'avatar-preset-9', name: '樱影', url: avatarAssetUrl('09-anime-sakura.webp') },
  { id: 'avatar-preset-10', name: '月蓝', url: avatarAssetUrl('10-anime-moon.webp') },
  { id: 'avatar-preset-11', name: '赛博', url: avatarAssetUrl('11-anime-cyber.webp') },
  { id: 'avatar-preset-12', name: '茶昼', url: avatarAssetUrl('12-anime-tea.webp') },
  { id: 'avatar-preset-13', name: '猫机', url: avatarAssetUrl('13-clay-robot.webp') },
  { id: 'avatar-preset-14', name: '星猫', url: avatarAssetUrl('14-pixel-sky.webp') },
  { id: 'avatar-preset-15', name: '水母', url: avatarAssetUrl('15-glass-orbit.webp') },
  { id: 'avatar-preset-16', name: '花冠', url: avatarAssetUrl('16-paper-flower.webp') },
  { id: 'avatar-preset-17', name: '墨发', url: avatarAssetUrl('17-ink-portrait.webp') },
  { id: 'avatar-preset-18', name: '狐镜', url: avatarAssetUrl('18-cyber-mask.webp') },
  { id: 'avatar-preset-19', name: '星球', url: avatarAssetUrl('19-soft-planet.webp') },
  { id: 'avatar-preset-20', name: '胶片', url: avatarAssetUrl('20-retro-camera.webp') },
  { id: 'avatar-preset-21', name: '雨窗男', url: avatarAssetUrl('21-rain-window-left.webp') },
  { id: 'avatar-preset-22', name: '雨窗女', url: avatarAssetUrl('22-rain-window-right.webp') },
  { id: 'avatar-preset-23', name: '星桥男', url: avatarAssetUrl('23-star-bridge-left.webp') },
  { id: 'avatar-preset-24', name: '星桥女', url: avatarAssetUrl('24-star-bridge-right.webp') },
  { id: 'avatar-preset-25', name: '咖啡男', url: avatarAssetUrl('25-coffee-table-left.webp') },
  { id: 'avatar-preset-26', name: '咖啡女', url: avatarAssetUrl('26-coffee-table-right.webp') },
  { id: 'avatar-preset-27', name: '狐帽', url: avatarAssetUrl('27-forest-runner.webp') },
  { id: 'avatar-preset-28', name: '暮城', url: avatarAssetUrl('28-city-dusk.webp') },
  { id: 'avatar-preset-29', name: '湖蓝', url: avatarAssetUrl('29-watercolor-lake.webp') },
  { id: 'avatar-preset-30', name: '游光', url: avatarAssetUrl('30-game-avatar.webp') },
]

export const DEFAULT_SELF_AVATAR_URL = AVATAR_PRESETS[0].url
export const DEFAULT_OTHER_AVATAR_URL = AVATAR_PRESETS[1].url
