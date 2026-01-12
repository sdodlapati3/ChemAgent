# Query Progress Streaming Analysis

## ✅ IMPLEMENTED (January 12, 2026)

### What's Now Available

1. **Real-time Progress Callbacks** in executor
2. **User-friendly Tool Descriptions** (40+ tools)
3. **SSE Streaming Endpoint** (`/query/stream`) with real progress
4. **Progress Event Schema** with all stages

### SSE Event Flow Example
```
→ {"status": "parsing", "message": "Understanding your question..."}
→ {"status": "parsed", "intent": "compound_lookup", "entities": 1}
→ {"status": "planning", "message": "Creating execution plan..."}
→ {"status": "planned", "steps": 3, "step_descriptions": [...]}
→ {"status": "executing", "step": 1, "total_steps": 3, "tool_description": "Searching ChEMBL database..."}
→ {"status": "step_complete", "step": 1, "step_result": {"success": true, "duration_ms": 245}}
→ {"status": "executing", "step": 2, ...}
→ {"status": "step_complete", "step": 2, ...}
→ {"status": "executing", "step": 3, ...}
→ {"status": "step_complete", "step": 3, ...}
→ {"status": "complete", "success": true, "execution_time_ms": 892, "result": {...}}
→ {"status": "stream_end"}
```

---

## Current State

### What We Have ✅
1. **SSE Endpoint** (`/query/stream`) - Already implemented in `server.py`
2. **StreamingResponse** - FastAPI integration ready
3. **Progress Events Structure** - JSON-formatted SSE events

### Current Streaming Flow
```
Client → POST /query/stream → Server
         ↓
    parsing → parsed → planning → planned → executing → complete
         ↓
    SSE Events back to Client
```

### Current Limitation ⚠️
The executor doesn't yield **real-time** step progress. Steps 5-7 in `event_generator()` are **simulated**:
```python
# Current: Simulated progress (executes all, then loops)
for i, step in enumerate(plan.steps):
    yield f"data: {...'executing', 'step': i + 1...}\n\n"
    await asyncio.sleep(0.1)  # Fake delay
```

---

## Recommendation: Implement Now (Phase 4.5)

**Reasons:**
1. **UX Critical** - Users expect feedback for 2-30 second queries
2. **Infrastructure Ready** - SSE endpoint exists, just needs executor integration
3. **Low Complexity** - 1-2 day effort
4. **Independent** - Doesn't block multi-agent work

---

## Implementation Plan

### Option A: Callback-Based Progress (Recommended)
**Complexity: Medium | Time: 4-6 hours**

```python
# executor.py - Add callback support
class QueryExecutor:
    def execute(
        self, 
        plan: QueryPlan,
        progress_callback: Optional[Callable[[str, int, int, str], None]] = None
    ) -> ExecutionResult:
        for i, step in enumerate(plan.steps):
            if progress_callback:
                progress_callback("executing", i + 1, len(plan.steps), step.tool_name)
            # ... execute step
```

```python
# server.py - Use callback in streaming
async def event_generator():
    progress_queue = asyncio.Queue()
    
    def on_progress(status, step, total, tool):
        progress_queue.put_nowait({"status": status, "step": step, "total": total, "tool": tool})
    
    # Run executor in background with callback
    async def run_executor():
        return state.executor.execute(plan, progress_callback=on_progress)
    
    task = asyncio.create_task(run_executor())
    
    # Yield progress events as they arrive
    while not task.done():
        try:
            event = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
            yield f"data: {json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            continue
    
    result = await task
    yield f"data: {json.dumps({'status': 'complete', 'result': result})}\n\n"
```

### Option B: AsyncIO Generator Executor
**Complexity: High | Time: 1-2 days**

Convert executor to async generator that yields progress:
```python
async def execute_async(self, plan: QueryPlan) -> AsyncGenerator[ProgressEvent, None]:
    for step in plan.steps:
        yield ProgressEvent("executing", step.tool_name)
        result = await self._execute_step(step)
        yield ProgressEvent("step_complete", result)
    yield ProgressEvent("complete", final_result)
```

### Option C: WebSocket (Future Enhancement)
**Complexity: High | Time: 2-3 days**

Better for bi-directional communication (user cancellation, etc.)

---

## Frontend Integration

### React/Next.js Example
```javascript
// useQueryStream.ts
export function useQueryStream() {
  const [progress, setProgress] = useState({ status: 'idle', step: 0, total: 0 });
  
  const executeQuery = async (query: string) => {
    const eventSource = new EventSource(`/api/query/stream?q=${encodeURIComponent(query)}`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(data);
      
      if (data.status === 'complete' || data.status === 'error') {
        eventSource.close();
      }
    };
  };
  
  return { progress, executeQuery };
}
```

### Progress UI Component
```jsx
function QueryProgress({ status, step, total, tool }) {
  const stages = ['parsing', 'planning', 'executing', 'complete'];
  
  return (
    <div className="progress-container">
      {/* Stage indicators */}
      <div className="stages">
        {stages.map(s => (
          <div key={s} className={`stage ${status === s ? 'active' : ''}`}>
            {s === 'executing' ? `Step ${step}/${total}: ${tool}` : s}
          </div>
        ))}
      </div>
      
      {/* Progress bar */}
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${(step / total) * 100}%` }}
        />
      </div>
      
      {/* Status message */}
      <div className="status-message">
        {status === 'parsing' && '🔍 Understanding your question...'}
        {status === 'planning' && '📋 Creating execution plan...'}
        {status === 'executing' && `⚙️ Running ${tool}...`}
        {status === 'complete' && '✅ Complete!'}
      </div>
    </div>
  );
}
```

---

## Progress Event Schema

```typescript
interface ProgressEvent {
  status: 'parsing' | 'parsed' | 'planning' | 'planned' | 'executing' | 'step_complete' | 'complete' | 'error';
  
  // For parsed status
  intent?: string;
  entities?: number;
  
  // For planned status
  steps?: number;
  parallel_groups?: number;
  
  // For executing status
  step?: number;
  total?: number;
  tool?: string;
  tool_description?: string;
  
  // For step_complete status
  step_result?: {
    success: boolean;
    duration_ms: number;
  };
  
  // For complete status
  result?: any;
  execution_time_ms?: number;
  
  // For error status
  error?: string;
  traceback?: string;
}
```

---

## Decision Matrix

| Factor | Implement Now | Defer to Multi-Agent |
|--------|--------------|---------------------|
| **User Value** | High - immediate feedback | Same |
| **Complexity** | Low (Option A) | Higher (needs agent coordination) |
| **Dependencies** | None | Agent framework |
| **Reusability** | Yes - same pattern for agents | Yes |
| **Time** | 4-6 hours | Part of larger effort |

**Recommendation: Implement Option A Now**

The callback-based approach is:
1. Simple to implement
2. Doesn't require restructuring executor
3. Provides real progress updates
4. Easily extensible for multi-agent (each agent can have its own callback)

---

## Implementation Checklist

- [ ] Add `progress_callback` parameter to `QueryExecutor.execute()`
- [ ] Update executor to call callback at each step
- [ ] Modify `/query/stream` to use async queue pattern
- [ ] Add tool descriptions for user-friendly messages
- [ ] Test with frontend
- [ ] Add timeout/cancellation support (optional)
