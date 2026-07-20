-- Varve — Seed Data Script matching seed-narrative.md exactly

-- Clean up existing data to allow clean re-runs
TRUNCATE findings, incidents, business_metrics, lineage_events CASCADE;

-- Fixed UUIDs for predictable reference
DO $$
DECLARE
    event_story1_id  UUID := 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
    event_story2_id  UUID := 'b2c3d4e5-f6a7-8901-bcde-f23456789012';
    event_story3a_id UUID := 'c3c4d5e6-f7a8-9012-bcde-f34567890123';
    event_story3b_id UUID := 'd4e5f6a7-b8c9-0123-def0-456789012345';
    event_story4_id  UUID := 'e5f6a7b8-c9d0-1234-ef01-567890123456';
BEGIN

    -- ============================================================
    -- 1. LINEAGE EVENTS
    -- ============================================================

    -- Story 1: Undocumented threshold modification by J. Alvarez on customers dataset
    INSERT INTO lineage_events (
        event_id,
        model_id,
        node_type,
        node_urn,
        event_type,
        event_timestamp,
        actor,
        actor_departed_within_90d,
        documentation_present
    ) VALUES (
        event_story1_id,
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)',
        'threshold',
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.customers,PROD)',
        'modified',
        '2026-05-20 10:00:00+00',
        'J. Alvarez',
        TRUE,
        FALSE
    );

    -- Story 2: Undocumented column added by R. Chen on products dataset
    INSERT INTO lineage_events (
        event_id,
        model_id,
        node_type,
        node_urn,
        event_type,
        event_timestamp,
        actor,
        actor_departed_within_90d,
        documentation_present
    ) VALUES (
        event_story2_id,
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.products,PROD)',
        'feature',
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.products,PROD)',
        'added',
        '2026-06-01 11:15:00+00',
        'R. Chen',
        FALSE,
        FALSE
    );

    -- Story 3 (Model A): Undocumented change by J. Alvarez on addresses dataset (before departure)
    INSERT INTO lineage_events (
        event_id,
        model_id,
        node_type,
        node_urn,
        event_type,
        event_timestamp,
        actor,
        actor_departed_within_90d,
        documentation_present
    ) VALUES (
        event_story3a_id,
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.addresses,PROD)',
        'pipeline_step',
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.addresses,PROD)',
        'modified',
        '2026-04-10 09:00:00+00',
        'J. Alvarez',
        TRUE,
        FALSE
    );

    -- Story 3 (Model B): Secondary edit by J. Alvarez on order_items dataset
    INSERT INTO lineage_events (
        event_id,
        model_id,
        node_type,
        node_urn,
        event_type,
        event_timestamp,
        actor,
        actor_departed_within_90d,
        documentation_present
    ) VALUES (
        event_story3b_id,
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.order_items,PROD)',
        'feature',
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.order_items,PROD)',
        'added',
        '2026-04-15 14:00:00+00',
        'J. Alvarez',
        TRUE,
        FALSE
    );

    -- ============================================================
    -- 2. INCIDENTS
    -- ============================================================

    -- Story 1 Incident: Downstream miscategorization on order_details table
    INSERT INTO incidents (
        incident_id,
        model_id,
        detected_at,
        resolved_at,
        root_cause_event_id,
        description,
        fix_summary
    ) VALUES (
        'c3d4e5f6-a7b8-9012-cdef-345678901234',
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)',
        '2026-07-08 14:30:00+00',
        '2026-07-19 17:00:00+00',
        event_story1_id,
        'Customer records miscategorized in order_details table due to unreviewed threshold change in upstream customers dataset.',
        'Reverted threshold logic in customers transformation and reprocessed historical order_details partitions.'
    );

    -- Story 3 Incident (Model B): Data corruption on order_items caused by Model A (addresses) event!
    INSERT INTO incidents (
        incident_id,
        model_id,
        detected_at,
        resolved_at,
        root_cause_event_id,
        description,
        fix_summary
    ) VALUES (
        'd4e5f6a7-b8c9-0123-def0-567890123456',
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.order_items,PROD)',
        '2026-06-15 11:00:00+00',
        '2026-06-29 18:00:00+00',
        event_story3a_id,  -- Points to addresses (Model A)!
        'Order item sync failure on order_items dataset due to unreviewed transformation logic in upstream addresses dataset.',
        'Repaired addresses transformation pipeline and resynced order_items records.'
    );

    -- ============================================================
    -- 3. BUSINESS METRICS
    -- ============================================================

    -- Story 1 Metrics for order_details categorization accuracy
    INSERT INTO business_metrics (model_id, metric_name, value, recorded_at) VALUES
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)', 'categorization_accuracy', 96.5, '2026-05-19 00:00:00+00'),
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)', 'categorization_accuracy', 96.2, '2026-05-25 00:00:00+00'),
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.ORDER_ENTRY_DB.analytics.order_details,PROD)', 'categorization_accuracy', 82.1, '2026-07-08 14:00:00+00');

    -- Story 2 Metrics for products (stable metric history)
    INSERT INTO business_metrics (model_id, metric_name, value, recorded_at) VALUES
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.products,PROD)', 'schema_validity_score', 99.8, '2026-05-30 00:00:00+00'),
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.products,PROD)', 'schema_validity_score', 99.9, '2026-06-05 00:00:00+00'),
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.products,PROD)', 'schema_validity_score', 99.9, '2026-07-15 00:00:00+00');

    -- Story 3 Metrics for order_items fulfillment error rate
    INSERT INTO business_metrics (model_id, metric_name, value, recorded_at) VALUES
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.order_items,PROD)', 'fulfillment_sync_error_rate', 0.1, '2026-04-09 00:00:00+00'),
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.order_items,PROD)', 'fulfillment_sync_error_rate', 0.2, '2026-04-12 00:00:00+00'),
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.order_items,PROD)', 'fulfillment_sync_error_rate', 8.4, '2026-06-15 11:00:00+00');

    -- ============================================================
    -- Story 4: M. Santos — Undocumented threshold change on countries (ZERO incidents — downgrade demo)
    -- ============================================================
    INSERT INTO lineage_events (
        event_id,
        model_id,
        node_type,
        node_urn,
        event_type,
        event_timestamp,
        actor,
        actor_departed_within_90d,
        documentation_present
    ) VALUES (
        event_story4_id,
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.countries,PROD)',
        'threshold',
        'urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.countries,PROD)',
        'modified',
        '2026-07-01 15:30:00+00',
        'M. Santos',
        FALSE,
        FALSE
    );
    -- No incidents row for Story 4 — zero precedent is the point.
    -- Story 4 Metrics (countries — stable, no spike)
    INSERT INTO business_metrics (model_id, metric_name, value, recorded_at) VALUES
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.countries,PROD)', 'schema_validity_score', 100.0, '2026-06-30 00:00:00+00'),
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.countries,PROD)', 'schema_validity_score', 100.0, '2026-07-02 00:00:00+00'),
    ('urn:li:dataset:(urn:li:dataPlatform:dbt,b2fd91.order_entry_db.order_entry.countries,PROD)', 'schema_validity_score', 100.0, '2026-07-15 00:00:00+00');

END $$;
