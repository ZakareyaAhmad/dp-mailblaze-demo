{{ config(
    materialized='incremental',
    unique_key='event_id'
) }}

select *
from {{ ref('int_events') }}

{% if is_incremental() %}

  where INGESTED_AT > (
      select max(INGESTED_AT)
      from {{ this }}
  )

{% endif %}