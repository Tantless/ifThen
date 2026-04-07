function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

export async function probeHealth(url: string): Promise<boolean> {
  try {
    const response = await fetch(url, {
      signal: AbortSignal.timeout(2_000),
    })
    return response.ok
  } catch {
    return false
  }
}

export async function waitForHealth(url: string, timeoutMs = 15_000, intervalMs = 500): Promise<boolean> {
  const deadline = Date.now() + timeoutMs

  while (Date.now() < deadline) {
    if (await probeHealth(url)) {
      return true
    }

    await delay(intervalMs)
  }

  return false
}
