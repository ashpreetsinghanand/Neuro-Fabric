"""
LangChain tools for data quality analysis.
Performs per-column and per-table statistical analysis via SQL.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool
from sqlalchemy import text

from core.db_connectors import get_engine

logger = logging.getLogger(__name__)


def _engine(db_config: dict):
    return get_engine(db_config or {})


# ---------------------------------------------------------------------------
# Tool: analyze_column_nulls
# ---------------------------------------------------------------------------

@tool
def analyze_column_nulls(
    table_name: str,
    column_name: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Compute null count and null rate for a specific column.

    Args:
        table_name: Target table.
        column_name: Column to analyze.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with null_count, total_rows, null_rate.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    try:
        q = text(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(*) FILTER (WHERE "{column_name}" IS NULL) AS null_count
            FROM "{schema_name}"."{table_name}"
            """
        )
        with engine.connect() as conn:
            row = conn.execute(q).mappings().one()
        total = row["total_rows"] or 1
        null_count = row["null_count"]
        return json.dumps({
            "table": table_name,
            "column": column_name,
            "total_rows": total,
            "null_count": null_count,
            "null_rate": round(null_count / total, 4),
        })
    except Exception as exc:
        logger.error("analyze_column_nulls failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: analyze_column_stats
# ---------------------------------------------------------------------------

@tool
def analyze_column_stats(
    table_name: str,
    column_name: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Compute distinct count, min, max, mean, and stddev for a column.
    Numeric statistics are only returned for numeric/date columns.

    Args:
        table_name: Target table.
        column_name: Column to analyze.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with distinct_count, min_value, max_value, mean_value, std_dev.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    try:
        # Cast-safe approach: attempt numeric stats, catch if non-numeric
        q_base = text(
            f"""
            SELECT
                COUNT(DISTINCT "{column_name}") AS distinct_count,
                MIN("{column_name}"::text) AS min_value,
                MAX("{column_name}"::text) AS max_value
            FROM "{schema_name}"."{table_name}"
            """
        )
        q_numeric = text(
            f"""
            SELECT
                AVG("{column_name}"::numeric) AS mean_value,
                STDDEV("{column_name}"::numeric) AS std_dev
            FROM "{schema_name}"."{table_name}"
            """
        )
        with engine.connect() as conn:
            base_row = conn.execute(q_base).mappings().one()
            try:
                num_row = conn.execute(q_numeric).mappings().one()
                mean_value = float(num_row["mean_value"]) if num_row["mean_value"] is not None else None
                std_dev = float(num_row["std_dev"]) if num_row["std_dev"] is not None else None
            except Exception:
                mean_value = None
                std_dev = None

        return json.dumps({
            "table": table_name,
            "column": column_name,
            "distinct_count": base_row["distinct_count"],
            "min_value": base_row["min_value"],
            "max_value": base_row["max_value"],
            "mean_value": mean_value,
            "std_dev": std_dev,
        })
    except Exception as exc:
        logger.error("analyze_column_stats failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: check_pk_uniqueness
# ---------------------------------------------------------------------------

@tool
def check_pk_uniqueness(
    table_name: str,
    pk_columns: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Check primary key uniqueness health: fraction of rows with unique PK values.

    Args:
        table_name: Target table.
        pk_columns: Comma-separated list of PK column names.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with total_rows, unique_pk_rows, uniqueness_rate.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    cols = [c.strip() for c in pk_columns.split(",")]
    col_expr = ", ".join(f'"{c}"' for c in cols)
    try:
        q = text(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(*) OVER () - COUNT(*) AS duplicate_count,
                (SELECT COUNT(*) FROM (
                    SELECT {col_expr} FROM "{schema_name}"."{table_name}"
                    GROUP BY {col_expr}
                ) AS t) AS unique_pk_rows
            FROM "{schema_name}"."{table_name}"
            LIMIT 1
            """
        )
        # Simpler alternative for all DB types
        q2 = text(
            f"""
            SELECT
                (SELECT COUNT(*) FROM "{schema_name}"."{table_name}") AS total_rows,
                (SELECT COUNT(*) FROM (
                    SELECT {col_expr} FROM "{schema_name}"."{table_name}"
                    GROUP BY {col_expr}
                ) AS sub) AS unique_pk_rows
            """
        )
        with engine.connect() as conn:
            row = conn.execute(q2).mappings().one()
        total = row["total_rows"] or 1
        unique = row["unique_pk_rows"]
        return json.dumps({
            "table": table_name,
            "pk_columns": cols,
            "total_rows": total,
            "unique_pk_rows": unique,
            "uniqueness_rate": round(unique / total, 4),
        })
    except Exception as exc:
        logger.error("check_pk_uniqueness failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: check_freshness
# ---------------------------------------------------------------------------

@tool
def check_freshness(
    table_name: str,
    timestamp_column: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Check data freshness using a timestamp column: latest and oldest records.

    Args:
        table_name: Target table.
        timestamp_column: The datetime/timestamp column to use.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with latest_record, oldest_record, age_days.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    try:
        q = text(
            f"""
            SELECT
                MAX("{timestamp_column}") AS latest_record,
                MIN("{timestamp_column}") AS oldest_record,
                EXTRACT(EPOCH FROM (NOW() - MAX("{timestamp_column}"))) / 86400 AS age_days
            FROM "{schema_name}"."{table_name}"
            """
        )
        with engine.connect() as conn:
            row = conn.execute(q).mappings().one()
        return json.dumps({
            "table": table_name,
            "timestamp_column": timestamp_column,
            "latest_record": str(row["latest_record"]) if row["latest_record"] else None,
            "oldest_record": str(row["oldest_record"]) if row["oldest_record"] else None,
            "age_days": float(row["age_days"]) if row["age_days"] is not None else None,
        })
    except Exception as exc:
        logger.error("check_freshness failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: compute_table_completeness
# ---------------------------------------------------------------------------

@tool
def compute_table_completeness(
    table_name: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Compute overall table completeness: average non-null rate across all columns.

    Args:
        table_name: Target table.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.

    Returns:
        JSON with overall_completeness (0.0–1.0) and per-column null rates.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    from core.db_connectors import get_inspector
    inspector = get_inspector(engine)
    try:
        columns = [c["name"] for c in inspector.get_columns(table_name, schema=schema_name)]
        null_rate_exprs = ",\n".join(
            f'AVG(CASE WHEN "{c}" IS NULL THEN 1.0 ELSE 0.0 END) AS "{c}_null_rate"'
            for c in columns
        )
        q = text(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                {null_rate_exprs}
            FROM "{schema_name}"."{table_name}"
            """
        )
        with engine.connect() as conn:
            row = dict(conn.execute(q).mappings().one())

        per_col_null_rates: dict[str, float] = {}
        for c in columns:
            key = f"{c}_null_rate"
            val = row.get(key)
            per_col_null_rates[c] = round(float(val), 4) if val is not None else 0.0

        overall = 1.0 - (sum(per_col_null_rates.values()) / len(per_col_null_rates)) if per_col_null_rates else 1.0

        return json.dumps({
            "table": table_name,
            "total_rows": row.get("total_rows"),
            "overall_completeness": round(overall, 4),
            "column_null_rates": per_col_null_rates,
        })
    except Exception as exc:
        logger.error("compute_table_completeness failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: detect_outliers_zscore
# ---------------------------------------------------------------------------

@tool
def detect_outliers_zscore(
    table_name: str,
    column_name: str,
    schema_name: str = "public",
    threshold: float = 3.0,
    db_config_json: str = "{}",
) -> str:
    """
    Detect outliers using Z-score method. Values with |z-score| > threshold are outliers.
    
    Args:
        table_name: Target table.
        column_name: Numeric column to analyze.
        schema_name: Schema containing the table (default: 'public').
        threshold: Z-score threshold (default: 3.0, captures ~99.7% of normal distribution).
        db_config_json: JSON string with optional db connection config.
    
    Returns:
        JSON with outlier_count, outlier_percentage, mean, stddev, and sample outliers.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    try:
        # Calculate mean and stddev
        q_stats = text(f"""
            SELECT 
                AVG("{column_name}"::numeric) AS mean_val,
                STDDEV("{column_name}"::numeric) AS stddev_val,
                COUNT(*) AS total_rows
            FROM "{schema_name}"."{table_name}"
            WHERE "{column_name}" IS NOT NULL
        """)
        with engine.connect() as conn:
            stats = conn.execute(q_stats).mappings().one()
        
        mean_val = float(stats["mean_val"]) if stats["mean_val"] else 0
        stddev_val = float(stats["stddev_val"]) if stats["stddev_val"] else 0
        total_rows = stats["total_rows"] or 1
        
        if stddev_val == 0:
            return json.dumps({
                "table": table_name,
                "column": column_name,
                "error": "Standard deviation is zero - no variation in data",
                "outlier_count": 0,
                "outlier_percentage": 0
            })
        
        # Count outliers using Z-score
        q_outliers = text(f"""
            SELECT COUNT(*) AS outlier_count
            FROM "{schema_name}"."{table_name}"
            WHERE "{column_name}" IS NOT NULL
            AND ABS(("{column_name}"::numeric - {mean_val}) / {stddev_val}) > {threshold}
        """)
        with engine.connect() as conn:
            outlier_row = conn.execute(q_outliers).mappings().one()
        
        outlier_count = outlier_row["outlier_count"] or 0
        
        # Get sample outlier values
        q_sample = text(f"""
            SELECT "{column_name}" AS value,
                   ABS(("{column_name}"::numeric - {mean_val}) / {stddev_val}) AS zscore
            FROM "{schema_name}"."{table_name}"
            WHERE "{column_name}" IS NOT NULL
            AND ABS(("{column_name}"::numeric - {mean_val}) / {stddev_val}) > {threshold}
            ORDER BY zscore DESC
            LIMIT 5
        """)
        with engine.connect() as conn:
            sample_outliers = [{"value": float(r["value"]), "zscore": round(float(r["zscore"]), 2)} 
                              for r in conn.execute(q_sample).mappings().all()]
        
        return json.dumps({
            "table": table_name,
            "column": column_name,
            "method": "z-score",
            "threshold": threshold,
            "mean": round(mean_val, 4),
            "stddev": round(stddev_val, 4),
            "total_rows": total_rows,
            "outlier_count": outlier_count,
            "outlier_percentage": round(outlier_count / total_rows * 100, 2),
            "sample_outliers": sample_outliers
        })
    except Exception as exc:
        logger.error("detect_outliers_zscore failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: detect_outliers_iqr
# ---------------------------------------------------------------------------

@tool
def detect_outliers_iqr(
    table_name: str,
    column_name: str,
    schema_name: str = "public",
    multiplier: float = 1.5,
    db_config_json: str = "{}",
) -> str:
    """
    Detect outliers using IQR (Interquartile Range) method.
    Outliers are values below Q1 - multiplier*IQR or above Q3 + multiplier*IQR.
    
    Args:
        table_name: Target table.
        column_name: Numeric column to analyze.
        schema_name: Schema containing the table (default: 'public').
        multiplier: IQR multiplier (default: 1.5, standard for mild outliers).
        db_config_json: JSON string with optional db connection config.
    
    Returns:
        JSON with Q1, Q3, IQR, outlier bounds, and outlier count.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    try:
        q = text(f"""
            WITH stats AS (
                SELECT 
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "{column_name}"::numeric) AS q1,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "{column_name}"::numeric) AS q3,
                    COUNT(*) AS total_rows
                FROM "{schema_name}"."{table_name}"
                WHERE "{column_name}" IS NOT NULL
            )
            SELECT 
                q1, q3,
                q3 - q1 AS iqr,
                q1 - {multiplier} * (q3 - q1) AS lower_bound,
                q3 + {multiplier} * (q3 - q1) AS upper_bound,
                total_rows
            FROM stats
        """)
        with engine.connect() as conn:
            row = conn.execute(q).mappings().one()
        
        q1 = float(row["q1"]) if row["q1"] else 0
        q3 = float(row["q3"]) if row["q3"] else 0
        iqr = float(row["iqr"]) if row["iqr"] else 0
        lower_bound = float(row["lower_bound"]) if row["lower_bound"] else 0
        upper_bound = float(row["upper_bound"]) if row["upper_bound"] else 0
        total_rows = row["total_rows"] or 1
        
        # Count outliers
        q_count = text(f"""
            SELECT COUNT(*) AS outlier_count
            FROM "{schema_name}"."{table_name}"
            WHERE "{column_name}" IS NOT NULL
            AND ("{column_name}"::numeric < {lower_bound} OR "{column_name}"::numeric > {upper_bound})
        """)
        with engine.connect() as conn:
            outlier_row = conn.execute(q_count).mappings().one()
        
        outlier_count = outlier_row["outlier_count"] or 0
        
        return json.dumps({
            "table": table_name,
            "column": column_name,
            "method": "iqr",
            "multiplier": multiplier,
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
            "lower_bound": round(lower_bound, 4),
            "upper_bound": round(upper_bound, 4),
            "total_rows": total_rows,
            "outlier_count": outlier_count,
            "outlier_percentage": round(outlier_count / total_rows * 100, 2)
        })
    except Exception as exc:
        logger.error("detect_outliers_iqr failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: compute_distribution_stats
# ---------------------------------------------------------------------------

@tool
def compute_distribution_stats(
    table_name: str,
    column_name: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Compute advanced distribution statistics: skewness, kurtosis, percentiles.
    
    Args:
        table_name: Target table.
        column_name: Numeric column to analyze.
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.
    
    Returns:
        JSON with mean, median, mode, skewness, kurtosis, and percentile distribution.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    try:
        # Get basic stats and percentiles
        q = text(f"""
            SELECT 
                COUNT(*) AS total_rows,
                AVG("{column_name}"::numeric) AS mean_val,
                STDDEV("{column_name}"::numeric) AS stddev_val,
                VARIANCE("{column_name}"::numeric) AS variance_val,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "{column_name}"::numeric) AS median,
                PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY "{column_name}"::numeric) AS p10,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "{column_name}"::numeric) AS p25,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "{column_name}"::numeric) AS p75,
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY "{column_name}"::numeric) AS p90,
                MIN("{column_name}"::numeric) AS min_val,
                MAX("{column_name}"::numeric) AS max_val
            FROM "{schema_name}"."{table_name}"
            WHERE "{column_name}" IS NOT NULL
        """)
        with engine.connect() as conn:
            row = conn.execute(q).mappings().one()
        
        mean_val = float(row["mean_val"]) if row["mean_val"] else 0
        stddev_val = float(row["stddev_val"]) if row["stddev_val"] else 0
        variance_val = float(row["variance_val"]) if row["variance_val"] else 0
        median = float(row["median"]) if row["median"] else 0
        min_val = float(row["min_val"]) if row["min_val"] else 0
        max_val = float(row["max_val"]) if row["max_val"] else 0
        total_rows = row["total_rows"] or 1
        
        # Calculate skewness and kurtosis using DuckDB/Postgres
        # Skewness = E[(X-μ)³] / σ³
        # Kurtosis = E[(X-μ)⁴] / σ⁴ - 3
        q_skew = text(f"""
            SELECT 
                AVG(("{column_name}"::numeric - {mean_val})^3) / NULLIF({stddev_val}^3, 0) AS skewness,
                AVG(("{column_name}"::numeric - {mean_val})^4) / NULLIF({stddev_val}^4, 0) - 3 AS kurtosis
            FROM "{schema_name}"."{table_name}"
            WHERE "{column_name}" IS NOT NULL
        """)
        with engine.connect() as conn:
            skew_row = conn.execute(q_skew).mappings().one()
        
        skewness = float(skew_row["skewness"]) if skew_row["skewness"] else 0
        kurtosis = float(skew_row["kurtosis"]) if skew_row["kurtosis"] else 0
        
        # Interpret skewness
        skew_interpretation = "symmetric" if abs(skewness) < 0.5 else \
                             "moderately skewed" if abs(skewness) < 1 else "highly skewed"
        skew_direction = "right" if skewness > 0 else "left" if skewness < 0 else "none"
        
        # Interpret kurtosis
        kurtosis_interpretation = "mesokurtic (normal)" if abs(kurtosis) < 1 else \
                                  "leptokurtic (heavy tails)" if kurtosis > 1 else "platykurtic (light tails)"
        
        return json.dumps({
            "table": table_name,
            "column": column_name,
            "total_rows": total_rows,
            "mean": round(mean_val, 4),
            "median": round(median, 4),
            "stddev": round(stddev_val, 4),
            "variance": round(variance_val, 4),
            "min": round(min_val, 4),
            "max": round(max_val, 4),
            "range": round(max_val - min_val, 4),
            "skewness": round(skewness, 4),
            "skewness_interpretation": f"{skew_interpretation} ({skew_direction})",
            "kurtosis": round(kurtosis, 4),
            "kurtosis_interpretation": kurtosis_interpretation,
            "percentiles": {
                "p10": round(float(row["p10"]), 4) if row["p10"] else None,
                "p25": round(float(row["p25"]), 4) if row["p25"] else None,
                "p50": round(median, 4),
                "p75": round(float(row["p75"]), 4) if row["p75"] else None,
                "p90": round(float(row["p90"]), 4) if row["p90"] else None
            }
        })
    except Exception as exc:
        logger.error("compute_distribution_stats failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: benford_law_analysis
# ---------------------------------------------------------------------------

@tool
def benford_law_analysis(
    table_name: str,
    column_name: str,
    schema_name: str = "public",
    db_config_json: str = "{}",
) -> str:
    """
    Perform Benford's Law analysis for fraud detection.
    Benford's Law predicts the frequency of leading digits in naturally occurring data.
    Significant deviations may indicate data manipulation or fraud.
    
    Args:
        table_name: Target table.
        column_name: Numeric column to analyze (ideally financial/transactional data).
        schema_name: Schema containing the table (default: 'public').
        db_config_json: JSON string with optional db connection config.
    
    Returns:
        JSON with observed vs expected digit frequencies and fraud risk assessment.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    
    # Benford's Law expected frequencies
    benford_expected = {
        1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097, 5: 0.079,
        6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046
    }
    
    try:
        # Extract leading digits
        q = text(f"""
            SELECT 
                LEFT(ABS("{column_name}"::numeric)::text, 1)::int AS leading_digit,
                COUNT(*) AS count
            FROM "{schema_name}"."{table_name}"
            WHERE "{column_name}" IS NOT NULL
            AND "{column_name}"::numeric > 0
            AND LEFT(ABS("{column_name}"::numeric)::text, 1) ~ '^[1-9]$'
            GROUP BY 1
            ORDER BY 1
        """)
        with engine.connect() as conn:
            rows = conn.execute(q).mappings().all()
        
        total_count = sum(r["count"] for r in rows)
        if total_count == 0:
            return json.dumps({"error": "No valid positive numeric values found"})
        
        observed = {}
        chi_square = 0.0
        
        for r in rows:
            digit = r["leading_digit"]
            observed_count = r["count"]
            observed_pct = observed_count / total_count
            expected_pct = benford_expected.get(digit, 0)
            observed[digit] = {
                "count": observed_count,
                "observed_pct": round(observed_pct * 100, 2),
                "expected_pct": round(expected_pct * 100, 2),
                "deviation": round((observed_pct - expected_pct) * 100, 2)
            }
            # Chi-square contribution
            expected_count = expected_pct * total_count
            if expected_count > 0:
                chi_square += ((observed_count - expected_count) ** 2) / expected_count
        
        # Fill missing digits
        for d in range(1, 10):
            if d not in observed:
                observed[d] = {"count": 0, "observed_pct": 0, "expected_pct": round(benford_expected[d] * 100, 2), "deviation": round(-benford_expected[d] * 100, 2)}
        
        # Risk assessment based on chi-square
        # Critical values for df=8: 15.5 (p=0.05), 20.1 (p=0.01), 26.1 (p=0.001)
        if chi_square < 15.5:
            risk_level = "low"
            risk_message = "Data follows Benford's Law - no significant anomalies detected"
        elif chi_square < 20.1:
            risk_level = "moderate"
            risk_message = "Mild deviation from Benford's Law - review recommended"
        else:
            risk_level = "high"
            risk_message = "Significant deviation from Benford's Law - potential fraud or data manipulation"
        
        return json.dumps({
            "table": table_name,
            "column": column_name,
            "total_values_analyzed": total_count,
            "chi_square_statistic": round(chi_square, 4),
            "risk_level": risk_level,
            "risk_message": risk_message,
            "digit_distribution": observed
        })
    except Exception as exc:
        logger.error("benford_law_analysis failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool: compute_correlation_matrix
# ---------------------------------------------------------------------------

@tool
def compute_correlation_matrix(
    table_name: str,
    schema_name: str = "public",
    columns: str = "",
    db_config_json: str = "{}",
) -> str:
    """
    Compute Pearson correlation matrix between numeric columns.
    
    Args:
        table_name: Target table.
        schema_name: Schema containing the table (default: 'public').
        columns: Comma-separated list of numeric columns (if empty, uses all numeric columns).
        db_config_json: JSON string with optional db connection config.
    
    Returns:
        JSON with correlation matrix and significant correlations identified.
    """
    db_config = json.loads(db_config_json)
    engine = _engine(db_config)
    
    try:
        from core.db_connectors import get_inspector
        inspector = get_inspector(engine)
        
        # Get numeric columns
        if columns:
            numeric_cols = [c.strip() for c in columns.split(",")]
        else:
            all_cols = inspector.get_columns(table_name, schema=schema_name)
            numeric_types = {'integer', 'bigint', 'smallint', 'decimal', 'numeric', 'real', 'double precision', 'float', 'money'}
            numeric_cols = [c["name"] for c in all_cols if str(c.get("type", "")).lower() in numeric_types or 
                           any(t in str(c.get("type", "")).lower() for t in numeric_types)]
        
        if len(numeric_cols) < 2:
            return json.dumps({"error": "Need at least 2 numeric columns for correlation"})
        
        # Build correlation query
        corr_pairs = []
        matrix = {}
        
        for i, col1 in enumerate(numeric_cols):
            matrix[col1] = {}
            for j, col2 in enumerate(numeric_cols):
                if i == j:
                    matrix[col1][col2] = 1.0
                elif j > i:
                    q = text(f"""
                        SELECT CORR("{col1}"::numeric, "{col2}"::numeric) AS correlation
                        FROM "{schema_name}"."{table_name}"
                        WHERE "{col1}" IS NOT NULL AND "{col2}" IS NOT NULL
                    """)
                    with engine.connect() as conn:
                        row = conn.execute(q).mappings().one()
                    corr = float(row["correlation"]) if row["correlation"] else 0
                    matrix[col1][col2] = round(corr, 4)
                    matrix[col2] = matrix.get(col2, {})
                    matrix[col2][col1] = round(corr, 4)
                    
                    # Track significant correlations
                    if abs(corr) > 0.7:
                        corr_pairs.append({
                            "column_1": col1,
                            "column_2": col2,
                            "correlation": round(corr, 4),
                            "strength": "strong positive" if corr > 0.7 else "strong negative"
                        })
                    elif abs(corr) > 0.5:
                        corr_pairs.append({
                            "column_1": col1,
                            "column_2": col2,
                            "correlation": round(corr, 4),
                            "strength": "moderate positive" if corr > 0.5 else "moderate negative"
                        })
        
        return json.dumps({
            "table": table_name,
            "columns_analyzed": numeric_cols,
            "correlation_matrix": matrix,
            "significant_correlations": sorted(corr_pairs, key=lambda x: abs(x["correlation"]), reverse=True)
        })
    except Exception as exc:
        logger.error("compute_correlation_matrix failed: %s", exc)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# All quality tools
# ---------------------------------------------------------------------------

QUALITY_TOOLS = [
    analyze_column_nulls,
    analyze_column_stats,
    check_pk_uniqueness,
    check_freshness,
    compute_table_completeness,
    detect_outliers_zscore,
    detect_outliers_iqr,
    compute_distribution_stats,
    benford_law_analysis,
    compute_correlation_matrix,
]
