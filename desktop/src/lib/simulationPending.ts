import type { SimulationCreate } from '../types/api'

export function resolveSimulationPendingStageLabel(
  mode: SimulationCreate['mode'],
  turnCount: number,
): string {
  const normalizedTurnCount = Number.isFinite(turnCount) ? Math.max(1, Math.round(turnCount)) : 1

  if (mode !== 'short_thread' || normalizedTurnCount <= 1) {
    return '先判断改写影响，再生成对方首轮回复'
  }

  return `先判断改写影响，再生成首轮回复，最多续写 ${normalizedTurnCount - 1} 轮`
}
