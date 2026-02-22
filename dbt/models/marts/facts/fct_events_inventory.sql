{{ config(materialized='table') }}

select
    e.event_id,
    e.event_ts,
    e.sku,
    e.event_type,
    e.ingested_at as event_ingested_at,

    i.on_hand,
    i.warehouse_id,
    i.as_of_date

from {{ ref('int_events') }} e
left join {{ ref('int_inventory') }} i
    on e.sku = i.sku