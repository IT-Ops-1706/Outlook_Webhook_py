# Webhook Scalability & Capacity Planning

## Executive Summary

The current system logic (FastAPI + Asyncio) allows for high concurrency. However, scaling to **100+ mailboxes** with **concurrent bursts** requires careful tuning of infrastructure resources and rate limits.

**Estimated Throughput:**
- **Daily Volume:** ~20,000+ emails
- **Peak Burst:** Likely 100-500 emails/minute during peak hours
- **Current Capacity:** Capable, but attached file handling is the primary bottleneck.

---

## 1. Concurrency Model

The system uses Python's `asyncio` loop, which is highly efficient for I/O-bound tasks like this (waiting for Microsoft, waiting for Utility).

| Component | Concurrency Handling | Limit |
|-----------|----------------------|-------|
| **Incoming Webhooks** | handled by Uvicorn | Thousands/sec (very high) |
| **Microsoft Graph Fetch** | Async HTTP calls | Controlled by `MAX_CONCURRENT_FORWARDS` |
| **Utility Forwarding** | Async HTTP calls | Controlled by `MAX_CONCURRENT_FORWARDS` |

### The `MAX_CONCURRENT_FORWARDS` Setting
This setting (default: 25) limits how many emails are processed *exactly* at the same time.
- **Too Low (10):** Queue backs up during bursts, latency increases.
- **Too High (100+):** Risk of hitting Microsoft Rate Limits or OOM (Out of Memory) crash.

---

## 2. Resource Constraints

### ⚠️ Memory (RAM) - Critical
Attachments are the biggest risk.
- **Scenario:** 100 concurrent emails, each with a 5MB PDF.
- **Memory Load:** 100 * 5MB = **500MB** RAM usage instantly.
- **Risk:** If deployment has only 512MB RAM, the instance will crash during bursts.

**Recommendation:**
For 100+ concurrent mailboxes, ensure **at least 2GB RAM** (e.g., Render "Standard" instance or higher).

### ⚡ CPU
Parsing JSON and regex matching is cheap. CPU is rarely the bottleneck unless you are doing heavy encryption or image processing within the webhook itself (which you aren't).

---

## 3. Microsoft Graph Rate Limits

Microsoft throttles requests per tenant or per app.
- **Limit:** Typically ~2000 requests per second (rps) globally, but specific operations (like fetching attachments) have tighter quotas.
- **Risk:** If 100 webhooks fire instantly, you trigger 100 * (1 email fetch + 1 attachment list + N attachment downloads) = **300+ API calls** instantly.

**Mitigation:**
The current code processes webhooks in batches. If 100 arrive, they are processed as fast as `MAX_CONCURRENT_FORWARDS` allows.
- **Safe Limit:** Keep `MAX_CONCURRENT_FORWARDS` under 50 to stay safe from Graph throttling.

---

## 4. Downstream Utility Limits

The webhook is a "pusher". It will push data to your Utility API as fast as possible.
- **Question:** Can your `ngrok` or internal server handle 25-50 concurrent POST requests?
- **Risk:** If the Utility is slow (checking OOC dates, DB writes), the webhook will hold connections open.
- **Timeout:** The webhook has a 30s timeout. If Utility takes >30s, the webhook will log an error and drop it.

---

## 5. Scaling Recommendations

### Phase 1: Tuning (Current Setup)
| Setting | Current | Recommendation for Scale |
|---------|---------|--------------------------|
| `MAX_CONCURRENT_FORWARDS` | 25 | **50** (if RAM allows) |
| Render Instance | Free/Starter | **Standard (Min 1GB RAM, ideally 2GB)** |
| LOG_LEVEL | INFO | **WARNING** (to save disk I/O log volume) |

### Phase 2: Architecture Upgrade (If >100,000 emails/day)
If you grow beyond the current plan, move to a **Queue-Worker Architecture**:

1. **Webhook Receiver (FastAPI):** Just acknowledges the webhook and pushes the notification ID to a queue (Redis/RabbitMQ). Response time: <10ms.
2. **Worker Pool:** Separate processes pull from Redis and process emails at a controlled rate.
   - Decouples ingestion from processing.
   - Handles massive bursts gracefully (queue just grows, doesn't crash RAM).

---

## 6. Max Capacity Implementation Plan

To support your goal of **100 mailboxes** receiving bursts:

1.  **Upgrade Server RAM:** Allocate 2GB+ RAM.
2.  **Increase Concurrency:** Set `MAX_CONCURRENT_FORWARDS=40`.
3.  **Active Monitoring:** Watch logs for `429 Too Many Requests` from Microsoft.
4.  **Utility Optimization:** Ensure your Utility API returns `200 OK` **immediately** (process in background) if possible, to free up the webhook logic.

### Estimated Capacity Table

| Metric | Capacity (Current Code) | Constraint |
|--------|-------------------------|------------|
| **Mailboxes** | Unlimited* | *Valid subscriptions required |
| **Max Concurrent Bursts** | ~50/sec | Microsoft Rate Limits |
| **Emails Per Day** | ~50,000+ | Depends on sustained rate |
| **Attachment Size** | Memory Dependent | ~25MB safe limit per file |

*Note: Microsoft Subscription limit is 10,000 per tenant using specific resource types, which is plenty for 100 mailboxes.*
