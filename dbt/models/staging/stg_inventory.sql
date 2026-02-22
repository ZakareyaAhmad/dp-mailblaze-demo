{{ config(materialized='view') }}

select
    INGESTED_AT,
    SOURCE_FILE,
    SKU,
    WAREHOUSE_ID,
    ON_HAND,
    AS_OF_DATE
from {{ source('raw', 'inventory_raw') }}