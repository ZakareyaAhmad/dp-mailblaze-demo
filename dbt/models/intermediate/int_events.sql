{{ config(materialized='view') }}

select
    INGESTED_AT,
    SOURCE_FILE,

    -- Extract fields from JSON
    PAYLOAD:"event_id"::string            as event_id,
    PAYLOAD:"event_ts"::timestamp_ntz     as event_ts,
    PAYLOAD:"idempotency_key"::string     as idempotency_key,
    PAYLOAD:"event_type"::string          as event_type,
    PAYLOAD:"campaign_id"::string         as campaign_id,
    PAYLOAD:"message_id"::string          as message_id,
    PAYLOAD:"recipient_email"::string     as recipient_email,
    PAYLOAD:"provider"::string            as provider,
    PAYLOAD:"sku"::string                 as sku

from {{ ref('stg_events') }}
where PAYLOAD is not null