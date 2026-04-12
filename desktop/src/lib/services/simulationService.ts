import { apiClient } from '../apiClient'
import type { SimulationCreate, SimulationJobRead, SimulationRead } from '../../types/api'

export function createSimulation(payload: SimulationCreate): Promise<SimulationJobRead> {
  return apiClient.post<SimulationJobRead>('/simulations', payload)
}

export function listConversationSimulationJobs(
  conversationId: number,
  limit?: number,
): Promise<SimulationJobRead[]> {
  const query = limit === undefined ? '' : `?limit=${limit}`
  return apiClient.get<SimulationJobRead[]>(`/conversations/${conversationId}/simulation-jobs${query}`)
}

export function readSimulation(simulationId: number): Promise<SimulationRead> {
  return apiClient.get<SimulationRead>(`/simulations/${simulationId}`)
}
