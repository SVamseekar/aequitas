"""DuckDB table definitions for the Aequitas warehouse.

Tables fall into two categories:
1. Core tables (schema-defined, loaded from Parquet via INSERT/COPY)
2. Analytics tables (created directly from processed Parquet via read_parquet)

The analytics tables use DuckDB's zero-copy Parquet scanning at build time.
All tables are read-only once the warehouse is built.
"""

# DDL for core tables — created first, data loaded separately
CORE_TABLES: dict[str, str] = {
    "stops": """
        CREATE TABLE IF NOT EXISTS stops (
            stop_id VARCHAR PRIMARY KEY,
            stop_name VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            lsoa_code VARCHAR,
            region_code VARCHAR,
            stop_type VARCHAR
        )
    """,
    "routes": """
        CREATE TABLE IF NOT EXISTS routes (
            route_id VARCHAR PRIMARY KEY,
            line_name VARCHAR,
            route_length_km DOUBLE,
            num_stops INTEGER,
            trips_per_day INTEGER,
            regions_served VARCHAR[],
            has_geometry BOOLEAN
        )
    """,
    "lsoa_demographics": """
        CREATE TABLE IF NOT EXISTS lsoa_demographics (
            lsoa_code VARCHAR PRIMARY KEY,
            lsoa_name VARCHAR,
            population INTEGER,
            imd_score DOUBLE,
            imd_decile INTEGER,
            unemployment_rate DOUBLE,
            nocar_pct DOUBLE,
            elderly_pct DOUBLE,
            income_score DOUBLE,
            nonwhite_pct DOUBLE,
            geo_barriers_score DOUBLE,
            urban_rural VARCHAR,
            disability_pct DOUBLE
        )
    """,
    "section_results": """
        CREATE TABLE IF NOT EXISTS section_results (
            region VARCHAR,
            urban_rural VARCHAR,
            section_id VARCHAR,
            stats JSON,
            chart_data JSON,
            narrative JSON,
            PRIMARY KEY (region, urban_rural, section_id)
        )
    """,
    "provenance": """
        CREATE TABLE IF NOT EXISTS provenance (
            metric_id VARCHAR PRIMARY KEY,
            value DOUBLE,
            formula VARCHAR,
            inputs JSON,
            source_files VARCHAR[]
        )
    """,
}

# Analytics tables — loaded directly from processed Parquet files.
# Key = table name, value = relative Parquet path (from warehouse root).
ANALYTICS_PARQUET_SOURCES: dict[str, str] = {
    "lsoa_service_quality": "data/processed/lsoa_service_quality.parquet",
    "lsoa_equity_metrics": "data/processed/lsoa_equity_metrics.parquet",
    "lsoa_accessibility": "data/processed/lsoa_2sfca.parquet",
    "lsoa_economic": "data/processed/lsoa_economic_appraisal.parquet",
    "lsoa_policy": "data/processed/lsoa_policy_synthesis.parquet",
    "route_details": "data/processed/route_geometries.parquet",
    "lta_readiness": "data/processed/lta_franchising_readiness.parquet",
    # New tables for expanded sections (all in data/audit/ — Phase 0 outputs)
    "stop_headways": "data/audit/stop_headways.parquet",
    "coverage_prediction": "data/audit/coverage_prediction.parquet",
    "shap_importance": "data/audit/shap_importance.parquet",
    "route_clusters": "data/audit/route_clusters.parquet",
    "lsoa_clusters": "data/audit/lsoa_clusters_hdbscan.parquet",
    "anomalies": "data/audit/anomalies.parquet",
    "modal_shift_scenarios": "data/audit/modal_shift_scenarios.parquet",
    "policy_scenarios": "data/audit/policy_scenarios.parquet",
}

# Combined: all table names in the warehouse
TABLES: dict[str, str] = {
    **CORE_TABLES,
    **{name: f"-- Parquet: {path}" for name, path in ANALYTICS_PARQUET_SOURCES.items()},
}
