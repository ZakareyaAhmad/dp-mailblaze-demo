{{ config(
    materialized = 'table'
) }}

with base as (

    select
        -- stable business grain (we want 1 row per warehouse+sku)
        warehouse_id,
        sku,

        -- descriptive / current-state attributes
        on_hand,
        as_of_date,

        -- lineage / audit
        ingested_at,
        source_file

    from {{ ref('stg_inventory') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by warehouse_id, sku
            order by as_of_date desc, ingested_at desc
        ) as rn
    from base

)

select
    -- surrogate key for easy joins/tests (stable across builds)
    {{ dbt_utils.generate_surrogate_key(['warehouse_id','sku']) }} as inventory_key,

    warehouse_id,
    sku,
    on_hand,
    as_of_date,
    ingested_at,
    source_file

from ranked
where rn = 1