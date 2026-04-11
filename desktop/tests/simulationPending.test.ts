import { describe, expect, it } from 'vitest'

import { resolveSimulationPendingStageLabel } from '../src/lib/simulationPending'

describe('resolveSimulationPendingStageLabel', () => {
  it('describes the real single-reply workflow without fake progress wording', () => {
    expect(resolveSimulationPendingStageLabel('single_reply', 1)).toBe('先判断改写影响，再生成对方首轮回复')
  })

  it('describes the short-thread workflow with the remaining follow-up turns', () => {
    expect(resolveSimulationPendingStageLabel('short_thread', 4)).toBe('先判断改写影响，再生成首轮回复，最多续写 3 轮')
  })

  it('falls back to the first-reply workflow when the short thread only asks for one turn', () => {
    expect(resolveSimulationPendingStageLabel('short_thread', 1)).toBe('先判断改写影响，再生成对方首轮回复')
  })
})
