# Testing Scripts

This directory contains scripts for testing and verifying the InGest-LLM.as service.

## test_webhook.py

Manual webhook testing script that allows you to test the Linear webhook integration without requiring actual webhook events from Linear.

### Usage

```bash
# Test local service (default)
python scripts/test_webhook.py

# Test with custom URL
python scripts/test_webhook.py --url http://localhost:8000

# Test production service
python scripts/test_webhook.py --url https://ingest.apexsigmasolutions.co.za

# Test with custom webhook secret
python scripts/test_webhook.py --secret "your-webhook-secret-from-linear"

# Quiet mode (minimal output)
python scripts/test_webhook.py --quiet

# Skip health check
python scripts/test_webhook.py --skip-health
```

### Requirements

```bash
pip install httpx
```

### What it tests

1. **Health Check** (`GET /webhook/health`)
   - Verifies the webhook forwarder is running
   - Checks health status response

2. **Webhook Endpoint** (`POST /webhook/linear`)
   - Sends a test Linear webhook payload
   - Generates proper HMAC-SHA256 signature
   - Validates response codes:
     - 200/202: Success (webhook accepted)
     - 503: Warning (forwarder up, but ingest-llm unavailable)
     - 401: Failure (invalid signature)
     - Other: Failure

### Example Output

```
======================================================================
HEALTH CHECK TEST
======================================================================

Target URL: http://localhost:8000/webhook/health

Response Status: 200

Response Body:
{
  "service": "webhook-forwarder",
  "status": "healthy",
  "target_url": "http://ingest-llm:8000",
  "timeout_seconds": 5
}

✓ HEALTH CHECK PASSED
  Webhook forwarder is healthy

======================================================================
WEBHOOK ENDPOINT TEST
======================================================================

Target URL: http://localhost:8000/webhook/linear
Secret: ***********

Test Payload:
{
  "type": "Issue",
  "action": "create",
  "data": {
    "id": "TEST-123",
    "title": "Test Issue from webhook testing script",
    ...
  }
}

Generated Signature: sha256=abc123...

Sending webhook request...

Response Status: 202

Response Body:
{
  "status": "forwarded",
  "correlation_id": "test-correlation-id-123",
  "message": "Webhook forwarded to ingest-llm service"
}

✓ TEST PASSED
  Webhook was accepted successfully

======================================================================
TEST SUMMARY
======================================================================
  Health Check: ✓ PASSED
  Webhook Test: ✓ PASSED

✓ All tests passed!
```

### Integration with CI/CD

The script can be used in automated testing:

```bash
# Exit code 0 on success, 1 on failure
if python scripts/test_webhook.py --quiet; then
    echo "Webhook tests passed"
else
    echo "Webhook tests failed"
    exit 1
fi
```

### Troubleshooting

**Connection refused:**
- Make sure the service is running on the specified URL
- Check that the port is correct (default: 8000)

**Invalid signature (401):**
- The webhook secret doesn't match `LINEAR_WEBHOOK_SECRET` in the service's environment
- Update the secret using `--secret` flag or update the service's `.env` file

**Service unavailable (503):**
- The webhook forwarder is running but cannot connect to `ingest-llm` service
- Check `FORWARDER_INGEST_LLM_URL` in environment variables
- Verify `ingest-llm` service is running

## Other Scripts

### run_core_integration_tests.py

Runs core integration tests for memOS integration.

```bash
python scripts/run_core_integration_tests.py
```

## Adding New Scripts

When adding new testing scripts:

1. Add execute permissions: `chmod +x scripts/your_script.py`
2. Include a docstring with usage examples
3. Add help text for all arguments
4. Document the script in this README
5. Make scripts work with both local and production environments
