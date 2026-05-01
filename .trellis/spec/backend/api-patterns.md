# API Patterns

> Common patterns and anti-patterns for API modules.

---

## Common Patterns

### 1. CRUD with Transaction

For creating entities with related data, use transactions.

```typescript
export function createProject(input: CreateProjectInput): CreateProjectOutput {
  const parseResult = createProjectInputSchema.safeParse(input);
  if (!parseResult.success) {
    return { success: false, error: parseResult.error.issues[0].message };
  }

  const { name, description, members } = parseResult.data;
  const projectId = crypto.randomUUID();

  try {
    const result = db.transaction((tx) => {
      // 1. Create project
      const [newProject] = tx
        .insert(project)
        .values({ id: projectId, name, description })
        .returning()
        .all();

      // 2. Create members if provided
      if (members && members.length > 0) {
        tx.insert(projectMember)
          .values(members.map((m) => ({ projectId, userId: m.userId })))
          .run();
      }

      return newProject;
    });

    // Note: Convert Date fields to Unix ms before returning
    // See shared/timestamp.md for specification
    return { success: true, project: result };
  } catch (error) {
    logger.error('Create failed', { error });
    return { success: false, error: 'Failed to create project' };
  }
}
```

### 2. Paginated List with Cursor

```typescript
export function listProjects(input: ListProjectsInput): ListProjectsOutput {
  const { status, limit = 20, cursor } = input;
  const conditions = [];

  if (status) {
    conditions.push(eq(project.status, status));
  }

  if (cursor) {
    const cursorData = decodeCursor(cursor);
    if (cursorData) {
      conditions.push(
        or(
          lt(project.updatedAt, cursorData.updatedAt),
          and(eq(project.updatedAt, cursorData.updatedAt), lt(project.id, cursorData.id))
        )
      );
    }
  }

  const fetchLimit = limit + 1;
  const results = db
    .select()
    .from(project)
    .where(conditions.length > 0 ? and(...conditions) : undefined)
    .orderBy(desc(project.updatedAt), desc(project.id))
    .limit(fetchLimit)
    .all();

  const hasMore = results.length > limit;
  if (hasMore) results.pop();

  const nextCursor =
    hasMore && results.length > 0
      ? encodeCursor(results[results.length - 1].updatedAt, results[results.length - 1].id)
      : null;

  return { success: true, projects: results, nextCursor, hasMore };
}
```

### 3. External API Call

Use `net.fetch` for proper proxy support.

```typescript
export async function fetchRemoteData(input: FetchRemoteInput): Promise<FetchRemoteOutput> {
  const parseResult = fetchRemoteInputSchema.safeParse(input);
  if (!parseResult.success) {
    return { success: false, error: parseResult.error.issues[0].message };
  }

  try {
    // Use net.fetch for proper proxy support
    const response = await net.fetch(`${API_URL}/resources/${input.id}`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${input.token}` },
    });

    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}` };
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return { success: false, error: 'Network request failed' };
  }
}
```

---

## Anti-Patterns

### 1. Fat IPC Handlers

```typescript
// BAD: Logic in IPC handler
ipcMain.handle("project:create", async (_, input) => {
  const parseResult = schema.safeParse(input);
  if (!parseResult.success) { ... }
  const [project] = db.insert(...).returning().all();
  return { success: true, project };
});

// GOOD: Thin IPC handler
ipcMain.handle("project:create", (_, input) => createProject(input));
```

### 2. Missing Validation

```typescript
// BAD: No validation
export function createProject(input: any) {
  db.insert(project).values(input).run();
}

// GOOD: Validate first
export function createProject(input: CreateProjectInput) {
  const parseResult = schema.safeParse(input);
  if (!parseResult.success) {
    return { success: false, error: parseResult.error.issues[0].message };
  }
  // ...
}
```

### 3. Node fetch Instead of net.fetch

```typescript
// BAD: Ignores system proxy
import fetch from 'node-fetch';
const response = await fetch(url);

// GOOD: Respects system proxy
import { net } from 'electron';
const response = await net.fetch(url);
```

### 4. Silent Return in Transactions

```typescript
// BAD: Transaction continues on failure
export function insertItem(tx, data) {
  const parseResult = schema.safeParse(data);
  if (!parseResult.success) {
    return; // Transaction continues!
  }
  tx.insert(table).values(data).run();
}

// GOOD: Throw to rollback
export function insertItem(tx, data) {
  const parseResult = schema.safeParse(data);
  if (!parseResult.success) {
    throw new Error('Validation failed');
  }
  tx.insert(table).values(data).run();
}
```

---

## Upsert Pattern

```typescript
db.insert(settings)
  .values({ key: 'theme', value: 'dark' })
  .onConflictDoUpdate({
    target: settings.key,
    set: { value: 'dark', updatedAt: new Date() },
  })
  .run();
```

---

## Soft Delete Pattern

```typescript
// Soft delete
db.update(project).set({ isDeleted: true, deletedAt: new Date() }).where(eq(project.id, id)).run();

// Query active only
db.select().from(project).where(eq(project.isDeleted, false)).all();
```

## Scenario: Analysis Job Structured Progress

### 1. Scope / Trigger

- Trigger: analysis worker progress is consumed by API clients and desktop UI.
- Use this contract whenever changing `AnalysisJob.payload_json["progress"]`, `JobRead`, or frontend analysis progress display.
- Do not require frontend code to parse human-readable `status_message`; stage state must be structured.

### 2. Signatures

Backend schema:

```python
class JobStageRead(BaseModel):
    id: str
    label: str
    status: str
    completed_units: int = 0
    total_units: int = 0


class JobRead(BaseModel):
    id: int
    status: str
    current_stage: str
    progress_percent: int
    current_stage_percent: int = 0
    current_stage_total_units: int = 0
    current_stage_completed_units: int = 0
    overall_total_units: int = 0
    overall_completed_units: int = 0
    status_message: str | None = None
    stages: list[JobStageRead] = Field(default_factory=list)
```

Worker payload:

```python
job.payload_json["progress"] = {
    "current_stage_total_units": int,
    "current_stage_completed_units": int,
    "overall_total_units": int,
    "overall_completed_units": int,
    "status_message": str,
    "stages": [
        {
            "id": "parsing" | "segmenting" | "summarizing" | "topic_resolution" | "persona" | "snapshots" | "completed",
            "label": str,
            "status": "waiting" | "running" | "completed" | "failed",
            "completed_units": int,
            "total_units": int,
        }
    ],
}
```

API formatter:

```python
def _job_progress_stages_to_read(raw_stages: object) -> list[JobStageRead]:
    ...
```

### 3. Contracts

- `stages` is additive and defaults to an empty list for legacy jobs.
- Stage IDs are stable machine-readable identifiers; labels are display text.
- Multiple stages may have `status == "running"` at the same time after segment summaries complete.
- `status_message` remains diagnostic text only. UI must not parse it for stage structure.
- `completed_units` and `total_units` are non-negative integers.
- Percent calculation is a view concern: `completed_units / total_units`; if `total_units <= 0`, display `0%`.
- Known stage order:
  1. `parsing`
  2. `segmenting`
  3. `summarizing`
  4. `topic_resolution`
  5. `persona`
  6. `snapshots`
  7. `completed`

### 4. Validation & Error Matrix

| Input / state | Required behavior |
| --- | --- |
| `progress["stages"]` missing | API returns `stages: []` |
| `progress["stages"]` is not a list | API returns `stages: []` |
| Stage item is not an object | Skip that item |
| Stage item lacks string `id`, `label`, or `status` | Skip that item |
| Numeric unit fields missing | Treat as `0` |
| Job fails while stages are running | Running stages should be marked `failed` before persisting failure progress |
| Multiple branches running | Preserve multiple `running` stage entries |

### 5. Good/Base/Bad Cases

Base legacy job:

```json
{
  "progress": {
    "current_stage_total_units": 11,
    "current_stage_completed_units": 11,
    "overall_total_units": 11,
    "overall_completed_units": 11,
    "status_message": "completed 11/11 units"
  }
}
```

API result must include:

```json
{ "stages": [] }
```

Good concurrent job:

```json
{
  "progress": {
    "stages": [
      {"id": "topic_resolution", "label": "话题整理", "status": "running", "completed_units": 12, "total_units": 47},
      {"id": "snapshots", "label": "关系快照", "status": "running", "completed_units": 7, "total_units": 47}
    ]
  }
}
```

Bad UI behavior:

```typescript
// Wrong: fragile string parsing
const isSnapshot = job.status_message?.includes("snapshots");
```

Correct UI behavior:

```typescript
const runningStages = job.stages.filter((stage) => stage.status === "running");
```

### 6. Tests Required

- Worker test: completed analysis job persists `progress.stages` with the expected stage IDs and terminal statuses.
- API test: legacy jobs without `progress.stages` serialize `stages: []`.
- Frontend adapter test: multiple running stages produce combined display text and per-stage progress values.
- Frontend shell/component test: always-visible analysis area does not render a global progress bar and exposes a details entry.

### 7. Wrong vs Correct

#### Wrong

```python
status_message = "topic_persona_snapshot 10/20 tasks (snapshots 7/14)"
```

This is acceptable as a diagnostic string, but not as the UI contract.

#### Correct

```python
payload["progress"]["stages"] = [
    {
        "id": "snapshots",
        "label": "关系快照",
        "status": "running",
        "completed_units": 7,
        "total_units": 14,
    }
]
```

---

## Summary

| Pattern           | Use Case           |
| ----------------- | ------------------ |
| Transaction       | Multiple writes    |
| Cursor pagination | Large lists        |
| net.fetch         | External API calls |
| Upsert            | Insert or update   |
| Soft delete       | Data recovery      |
