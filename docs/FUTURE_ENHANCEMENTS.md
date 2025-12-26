# Future Enhancements Documentation

##  Rate Limiting & Throttling

### Current State
- Basic concurrency control using semaphore (25 concurrent API calls)
- No per-utility limits
- No email volume throttling

### Why Needed
- Protect individual utility APIs from overload
- Prevent exceeding external API rate limits
- Control costs for paid APIs
- Handle email storms/spam

### Recommended Implementation

**Token Bucket Algorithm:**
```python
class RateLimiter:
    """Per-utility rate limiting"""
    
    def __init__(self):
        # Each utility gets own bucket
        self.buckets = {}
    
    async def acquire(self, utility_id: str, rate_per_second: int):
        # Refill tokens based on time passed
        # Check if tokens available
        # Consume token if available
        pass
```

**Configuration:**
```json
{
  "utility_id": "attachment_processor",
  "rate_limit": {
    "requests_per_second": 10,
    "burst_size": 50
  }
}
```

**Benefits:**
- Prevents overwhelming slow APIs
- Allows burst processing
- Configurable per utility
- Smooth API load

**When to implement:**
- You have 5+ utilities
- External APIs have rate limits
- Processing > 100 emails/minute

---

## Metrics & Monitoring

### Current State
- Basic logging to files
- No metrics collection
- No time-series data
- Manual log analysis

### Why Needed
- Understand system behavior
- Identify bottlenecks
- Track SLAs
- Capacity planning
- Alerting on issues

### Recommended Implementation

**Metrics to Track:**
```python
class Metrics:
    # Volume
    emails_received: int
    emails_processed: int
    emails_failed: int
    
    # Performance  
    avg_processing_time_ms: float
    p95_processing_time_ms: float
    p99_processing_time_ms: float
    
    # Utilities
    utility_success_rate: dict  # per utility
    utility_avg_response_time: dict
    
    # Infrastructure
    attachment_downloads: int
    retry_count: int
    circuit_breaker_open: list
```

**Metrics Endpoint:**
```
GET /metrics

{
  "period": "last_hour",
  "emails": {
    "received": 1250,
    "processed": 1245,
    "failed": 5
  },
  "performance": {
    "avg_time_ms": 450,
    "p95_time_ms": 1200
  },
  "utilities": {
    "attachment_processor": {
      "calls": 320,
      "success_rate": 99.7,
      "avg_response_ms": 850
    }
  }
}
```

**Integration Options:**
1. **Prometheus** - Industry standard, pull-based
2. **Datadog/NewRelic** - Commercial SaaS
3. **CloudWatch** - If on AWS
4. **Application Insights** - If on Azure

**Benefits:**
- Real-time dashboards
- Historical trends
- Alerting
- Capacity planning

**When to implement:**
- In production
- Processing > 50 emails/day
- Multiple utilities
- Need SLA tracking

---

## Configuration Validation

### Current State
- JSON file loaded directly
- No schema validation
- Runtime errors if config invalid
- Manual config checking

### Why Needed
- Catch config errors before deployment
- Prevent runtime failures
- Document config format
- Auto-complete in IDEs

### Recommended Implementation

**Pydantic Schemas:**
```python
from pydantic import BaseModel, validator

class FilterConfig(BaseModel):
    match_logic: str
    subject: Optional[dict]
    body: Optional[dict]
    
    @validator('match_logic')
    def validate_logic(cls, v):
        if v not in ['AND', 'OR']:
            raise ValueError('Must be AND or OR')
        return v

class UtilityConfig(BaseModel):
    id: str
    name: str
    enabled: bool
    subscriptions: dict
    pre_filters: FilterConfig
    endpoint: dict
    
    # Auto-validation on load
```

**Load with Validation:**
```python
def load_config():
    with open('config.json') as f:
        data = json.load(f)
    
    # Validate
    for utility in data['utilities']:
        UtilityConfig(**utility)  # Validates or raises
    
    return data
```

**Benefits:**
- Immediate error detection
- Clear error messages  
- Type safety
- Self-documenting

**When to implement:**
- Before production
- Multiple config editors
- Complex filter rules
- 5+ utilities

---

## Error Recovery Improvements

### Current State (Fail-Soft)
- Errors logged
- Processing continues
- No retry for failed emails
- No dead letter queue

### Better Options

**Option 1: Dead Letter Queue**
```python
class DeadLetterQueue:
    """Store failed processing attempts"""
    
    async def store_failed_email(
        self,
        email: EmailMetadata,
        utility_id: str,
        error: str,
        attempt_count: int
    ):
        # S tore in database or file
        # Allow manual retry later
        pass
```

**Option 2: Delayed Retry**
```python
class RetryScheduler:
    """Retry failed emails after delay"""
    
    async def schedule_retry(
        self,
        email: EmailMetadata,
        utility_id: str,
        delay_minutes: int
    ):
        # Schedule retry job
        # Exponential backoff
        pass
```

**Option 3: Circuit Breaker**
```python
class CircuitBreaker:
    """Stop calling failing utilities"""
    
    def __init__(self):
        self.failure_count = {}
        self.open_circuits = set()
    
    def record_failure(self, utility_id):
        # Track failures
        # Open circuit after threshold
        pass
    
    def is_open(self, utility_id) -> bool:
        # Check if should skip calls
        pass
```

**Option 4: Alert Webhooks**
```python
async def send_alert(
    alert_type: str,
    message: str,
    severity: str
):
    # Send to Slack/Teams/Email
    # Immediate notification of issues
    pass
```

**Comparison:**

| Option | Complexity | When to Use |
|--------|-----------|-------------|
| Dead Letter Queue | Medium | Production, critical emails |
| Delayed Retry | High | High-value processing |
| Circuit Breaker | Low | Protect from cascading failures |
| Alert Webhooks | Low | Always (easy win) |

**Recommendation:**
Start with Alert Webhooks, add Circuit Breaker, then Dead Letter Queue if needed.

---

## Summary

### Implement Now (Done)
- ✅ Attachment handling
- ✅ Basic retry (3 attempts)
- ✅ Processing logs (file-based)
- ✅ Security validation
- ✅ Error logging

### Implement Soon (Production Ready)
- Circuit Breaker (simple)
- Alert Webhooks (Slack/Teams)
- Metrics endpoint (basic)

### Implement Later (Scale/Enterprise)
- Advanced rate limiting
- Full metrics dashboard
- Configuration validation
- Dead letter queue
- Delayed retry system

### Decision Matrix

**You need this NOW if:**
- Processing > 100 emails/day: Metrics
- Multiple utilities: Circuit Breaker
- External API limits: Rate limiting
- Configuration errors: Validation

**You can wait if:**
- < 50 emails/day
- 1-2 utilities
- All APIs reliable
- Technical team only

---

## Next Steps

1. Deploy current enhancements
2. Test with real emails
3. Monitor for 1 week
4. Identify pain points
5. Implement next tier based on needs
