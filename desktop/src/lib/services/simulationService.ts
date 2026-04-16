import type { SimulationCreate, SimulationJobRead, SimulationRead } from '../../types/api'
import { requireDesktopBridge } from '../desktop'

export function createSimulation(payload: SimulationCreate): Promise<SimulationJobRead> {
  return requireDesktopBridge().simulations.create(payload)
}

export function listConversationSimulationJobs(
  conversationId: number,
  limit?: number,
): Promise<SimulationJobRead[]> {
  return requireDesktopBridge().simulations.listConversationJobs({ conversationId, limit })
}

export function readSimulation(simulationId: number): Promise<SimulationRead> {
  return requireDesktopBridge().simulations.read(simulationId)
}
