# Setup

## Prerequisites

- self-hosted n8n; the source system was built on `2.17.5`;
- a persistent writable `/files` volume;
- `ffmpeg` and `ffprobe` available to the n8n process;
- permission to use Execute Command, Read Binary File, and Write Binary File nodes;
- the Blotato community node used in workflows 06 and 07;
- accounts for only the services you intend to test.

Do not enable schedules or production webhooks during initial configuration.

## Import order

1. `01-telegram-source-ingestion.json`
2. `02-web-source-ingestion.json`
3. `03-ai-topic-curation.json`
4. `05-wordpress-publishing-pipeline.json`
5. `04-telegram-editorial-assistant.json`
6. `06-multichannel-text-distribution.json`
7. `07-ai-video-production-distribution.json`

Workflow 04 contains two sub-workflow nodes. After import:

- set `Call Topic Curation Workflow` to workflow 03;
- set `Call WordPress Publishing Workflow` to workflow 05.

The exported markers `SELECT_WORKFLOW_03_ID` and `SELECT_WORKFLOW_05_ID` are intentionally invalid until those selections are made.

## Credentials

No credential object or credential ID is included. Configure credentials in n8n and assign them to the relevant nodes.

| Credential type | Used by |
| --- | --- |
| Supabase API | 01-07 |
| OpenAI API | 03-07 |
| OpenRouter API | 03 and 05 |
| Telegram API | 03-07 |
| Google Drive OAuth2 | 05 |
| WordPress API | 05 |
| Blotato API | 06 and 07 |
| HeyGen API | 07 |

VK and MAX requests read their tokens from n8n runtime variables. For production, restrict access to those variables or migrate the requests to credential-backed authentication; never replace the expressions with literal tokens.

## n8n variables

Create the following instance/project variables:

| Variable | Required | Purpose |
| --- | --- | --- |
| `WORDPRESS_BASE_URL` | Yes for workflow 05 | WordPress origin only, for example `https://cms.example.com` |
| `CONTENT_OPS_WEBHOOK_SECRET` | Yes before publishing workflows 06/07 | Authenticates external WordPress webhooks |
| `MAX_API_TOKEN` | Yes for the MAX branch in workflow 06 | MAX request authorization |
| `VK_ACCESS_TOKEN` | Yes for the VK branches in workflows 06/07 | VK API authorization |
| `HEYGEN_AVATAR_ID_1` | Yes for workflow 07 | Presenter for content set 1 |
| `HEYGEN_AVATAR_ID_2` | Yes for workflow 07 | Presenter for content set 2 |
| `HEYGEN_AVATAR_ID_3` | Yes for workflow 07 | Presenter for content set 3 |
| `HEYGEN_VOICE_ID` | Yes for workflow 07 | Locked narrator voice |
| `HEYGEN_BRAND_KIT_ID` | Optional | HeyGen Brand System configuration |

`WORDPRESS_BASE_URL` must point to the same site configured in the WordPress credential and must not include a trailing path such as `/wp-json`.

## Webhook entry points

| Workflow | Webhook path | Authentication |
| --- | --- | --- |
| 06 · Text Distribution | `content-ops-text-webhook` | `X-Content-Ops-Secret` header preferred; body secret accepted for compatibility |
| 07 · Video Production | `content-ops-video-webhook` | `X-Content-Ops-Secret` header preferred; body secret accepted for compatibility |

Change the paths if they conflict with an existing instance. Keep both workflows inactive until the same high-entropy `CONTENT_OPS_WEBHOOK_SECRET` value is configured at the sender and in n8n.

## Configure placeholders

Search the imported workflows for `YOUR_` and `SELECT_`.

```text
YOUR_DZEN_CHANNEL
YOUR_GOOGLE_DRIVE_FILE_ID
YOUR_GOOGLE_DRIVE_FOLDER_ID
YOUR_MAX_CHANNEL
YOUR_MAX_CHAT_ID
YOUR_PLATFORM_ACCOUNT_ID
YOUR_SOURCE_CHANNEL
YOUR_TELEGRAM_CHAT_ID
YOUR_TELEGRAM_CHANNEL
YOUR_VK_COMMUNITY
YOUR_VK_OWNER_ID
SELECT_WORKFLOW_03_ID
SELECT_WORKFLOW_05_ID
```

Some markers are cached resource-locator values. Select the target account/file from the n8n node UI instead of typing the placeholder literally.

## Supabase

Create or map the logical tables listed in [DATA_CONTRACTS.md](DATA_CONTRACTS.md). Adapt field names and row-level security to the target Supabase environment.

At minimum, populate `system_settings` with the non-secret keys listed in the data-contract document. Keep API keys and webhook secrets outside this table.

## First run

1. Keep every workflow unpublished/inactive.
2. Configure one service at a time.
3. Use the Manual Trigger branch and `sample-data/` fixtures.
4. Replace publishing nodes with test accounts or disable them during dry runs.
5. Confirm database state changes and error branches.
6. Enable the webhook secret before exposing any webhook URL.
7. Publish schedules only after duplicate and failure-path tests pass.
