# UI Timeout Fix - Quick Reference

## Problem
Ingestion Playground UI shows "timeout of 5000ms exceeded" when parsing documents.

## Solution
Update the timeout in your fetch/axios call to 30 seconds (30000ms).

## Code Patches

### If using Fetch API:
```typescript
// FIND THIS:
fetch(url, {
  signal: AbortSignal.timeout(5000)
})

// REPLACE WITH:
fetch(url, {
  signal: AbortSignal.timeout(30000)  // 30 seconds for large documents
})
```

### If using Axios:
```typescript
// FIND THIS:
axios.post(url, data, { timeout: 5000 })

// REPLACE WITH:
axios.post(url, data, { timeout: 30000 })  // 30 seconds
```

### If using httpx (Python):
```python
# FIND THIS:
async with httpx.AsyncClient(timeout=5.0) as client:

# REPLACE WITH:
async with httpx.AsyncClient(timeout=30.0) as client:
```

## Dynamic Timeout (Recommended)
```typescript
const getTimeout = (textLength: number) => {
  if (textLength > 50000) return 60000;  // 60s for very large
  if (textLength > 10000) return 30000;  // 30s for large
  if (textLength > 1000) return 15000;   // 15s for medium
  return 5000;                            // 5s for small
};

const timeout = getTimeout(documentText.length);
fetch(url, { signal: AbortSignal.timeout(timeout) });
```

## Quick Test
After applying the fix, test with:
```bash
curl -X POST http://localhost:8000/graph/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"Your test document here"}'
```

Service is working correctly - this is purely a client-side timeout issue.
