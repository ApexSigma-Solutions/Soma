# InGest-LLM Graph Parser - Client Integration Guide

## Overview
The Graph Parser endpoint processes text into knowledge graphs using Spacy NLP. Processing time scales with document size.

## Endpoints

### 1. Parse Text (Full Document)
**Endpoint:** `POST /graph/parse`

**Request:**
```json
{
  "text": "Your document text here",
  "config": {}  // Optional
}
```

**Response:**
```json
{
  "metadata": {
    "model": "en_core_web_sm",
    "sentences_processed": 10,
    "nodes_extracted": 15,
    "edges_extracted": 12,
    "warning": "Large document (50000 chars) - processing may take 10-30s..."  // If applicable
  },
  "nodes": [...],
  "edges": [...]
}
```

### 2. Health Check
**Endpoint:** `GET /graph/health`

**Response:**
```json
{
  "status": "ready",
  "model_loaded": true,
  "model_name": "en_core_web_sm"
}
```

## Performance Guidelines

### Processing Times (Approximate)

| Document Size | Processing Time | Recommended Timeout |
|--------------|-----------------|---------------------|
| < 1,000 chars | 1-2 seconds | 5 seconds |
| 1,000 - 10,000 chars | 2-5 seconds | 10 seconds |
| 10,000 - 50,000 chars | 5-15 seconds | 30 seconds |
| 50,000+ chars | 15-60 seconds | 60+ seconds |

### Client Timeout Configuration

#### JavaScript/TypeScript (Fetch API)
```typescript
const response = await fetch('http://localhost:8000/graph/parse', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: documentText }),
  signal: AbortSignal.timeout(30000)  // 30 second timeout
});
```

#### Axios
```typescript
const response = await axios.post('http://localhost:8000/graph/parse', 
  { text: documentText },
  { timeout: 30000 }  // 30 second timeout
);
```

#### Python (requests)
```python
response = requests.post(
    'http://localhost:8000/graph/parse',
    json={'text': document_text},
    timeout=30  # 30 second timeout
)
```

## Best Practices

### 1. **Check Document Size Before Parsing**
```typescript
const MAX_SAFE_SIZE = 10000;  // chars

if (text.length > MAX_SAFE_SIZE) {
  // Show warning to user or chunk the document
  console.warn(`Large document (${text.length} chars) - may take 10-30s`);
  // Increase timeout
  timeout = 60000;
}
```

### 2. **Handle Timeouts Gracefully**
```typescript
try {
  const response = await parseDocument(text);
  // Handle success
} catch (error) {
  if (error.name === 'AbortError' || error.code === 'ECONNABORTED') {
    // Timeout occurred
    showError('Document is too large. Please try a smaller document or wait longer.');
  } else {
    // Other error
    showError('Parsing failed: ' + error.message);
  }
}
```

### 3. **Show Progress for Large Documents**
```typescript
async function parseWithProgress(text: string) {
  if (text.length > 10000) {
    showProgressIndicator('Parsing large document... This may take up to 30 seconds.');
  }
  
  try {
    const response = await fetch('/graph/parse', {
      method: 'POST',
      body: JSON.stringify({ text }),
      signal: AbortSignal.timeout(60000)
    });
    
    hideProgressIndicator();
    return await response.json();
  } catch (error) {
    hideProgressIndicator();
    throw error;
  }
}
```

### 4. **Chunk Large Documents (Optional)**
For very large documents (>100,000 chars), consider splitting:

```typescript
function chunkDocument(text: string, maxChunkSize: number = 50000): string[] {
  const chunks: string[] = [];
  const sentences = text.split(/[.!?]+\s+/);
  
  let currentChunk = '';
  for (const sentence of sentences) {
    if ((currentChunk + sentence).length > maxChunkSize) {
      chunks.push(currentChunk);
      currentChunk = sentence;
    } else {
      currentChunk += sentence + '. ';
    }
  }
  
  if (currentChunk) {
    chunks.push(currentChunk);
  }
  
  return chunks;
}

// Parse each chunk separately
async function parseChunked(text: string) {
  const chunks = chunkDocument(text);
  const results = await Promise.all(
    chunks.map(chunk => parseDocument(chunk))
  );
  
  // Merge results
  return mergeGraphResults(results);
}
```

## Troubleshooting

### "timeout of 5000ms exceeded"
**Solution:** Increase client timeout to at least 30 seconds for documents over 10,000 characters.

### "Parsing failed: NLTK punkt tokenizer not found"
**Solution:** The service needs to run the bootstrap script. This is now automatic on startup.

### "Parsing failed: No Spacy model could be loaded"
**Solution:** The service needs to run the bootstrap script. This is now automatic on startup.

### Slow Performance
**Causes:**
- Large document size (>50,000 chars)
- First request after service start (model loading)
- System resource constraints

**Solutions:**
- Chunk large documents
- Increase timeout
- Consider caching results for repeated parsing

## API Documentation

Full interactive API documentation available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Support

For issues or questions:
1. Check service logs: `InGest-LLM.as/logs/uvicorn_*.log`
2. Verify service health: `GET /health`
3. Check graph parser health: `GET /graph/health`
