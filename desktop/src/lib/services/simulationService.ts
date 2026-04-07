import { apiClient } from '../apiClient'
import type { SimulationCreate, SimulationRead } from '../../types/api'

export function createSimulation(payload: SimulationCreate): Promise<SimulationRead> {
  return apiClient.post<SimulationRead>('/simulations', payload)
}
