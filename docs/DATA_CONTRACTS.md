# Data contracts

This document describes the logical contracts visible in the workflows. It is not a complete Supabase migration and contains no production schema or records.

## Supabase tables

| Table | Minimum purpose |
| --- | --- |
| `system_settings` | Key/value operational configuration |
| `content_sources` | Active Telegram and website source registry |
| `content_themes` | Current topic, title, and keyword filters |
| `source_content` | Normalized source items used for curation |
| `knowledge_base` | Writing-style examples used by the drafting agent |
| `drafts` | Generated and edited drafts plus Telegram message state |
| `publications` | Publication queue, processing state, errors, and URLs |
| `n8n_chat_histories` | Previous topic selections used for deduplication |
| `system_monitoring` | Operational success/failure events |
| `video_jobs` | Video idempotency key, status, and final platform links |

## System settings referenced by the workflows

```text
admin_chat_id
ai_prompt_ideas_selector
ai_prompt_post_generator
days_before_ideas
default_channel_name
publishing_channel_chat_id
publishing_channel_identifier
publishing_channel_name
supabase_url
```

Store secrets in n8n Credentials or protected instance variables, not in `system_settings` rows that ordinary workflow users can read.

## Normalized source item

```json
{
  "platform": "telegram",
  "external_id": "source-post-123",
  "content": "A safe example source item.",
  "external_url": "https://example.com/source-post-123",
  "media_urls": [],
  "views_count": 0,
  "likes_count": 0,
  "published_at": "2026-09-01T08:00:00Z",
  "parsed_at": "2026-09-01T08:05:00Z"
}
```

## WordPress publication webhook

```json
{
  "secret": "SET_AT_RUNTIME",
  "post": {
    "ID": 1001,
    "post_title": "Three ways to improve cash-flow visibility",
    "post_content": "<p>Demonstration content.</p>",
    "post_status": "publish",
    "post_permalink": "https://example.com/sample-business-article/"
  },
  "post_thumbnail": "https://example.com/wp-content/uploads/sample-business-cover.jpg"
}
```

## Video-job state

```json
{
  "post_id": "sample-post-1001",
  "status": "processing",
  "received_at": "2026-09-01T09:00:00Z",
  "result_links": [],
  "error": null
}
```

Recommended status values:

```text
accepted → processing → generated → publishing → published
                              ↘ failed
accepted → skipped_duplicate
```

## Configuration placeholders

Values beginning with `YOUR_` or `SELECT_` are configuration markers. They are not real IDs and must be replaced before enabling external actions.
