import type { SettingRead, SettingWrite } from '../../types/api'
import { requireDesktopBridge } from '../desktop'

export function readSettings(): Promise<SettingRead[]> {
  return requireDesktopBridge().settings.read()
}

export function writeSetting(payload: SettingWrite): Promise<SettingRead> {
  return requireDesktopBridge().settings.write(payload)
}
