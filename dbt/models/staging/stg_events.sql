{{ config(materialized='view') }}

select
    INGESTED_AT,
    SOURCE_FILE,
    PAYLOAD
from {{ source('raw', 'email_events_raw') }}