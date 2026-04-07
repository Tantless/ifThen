import { apiClient } from '../apiClient'
import type { SettingRead, SettingWrite } from '../../types/api'

export function readSettings(): Promise<SettingRead[]> {
  return apiClient.get<SettingRead[]>('/settings')
}

export function writeSetting(payload: SettingWrite): Promise<SettingRead> {
  return apiClient.put<SettingRead>('/settings', payload)
}
