"""
Neo4j connector for Neuro-Fabric lineage graph.

Pushes schema metadata (tables, columns, FK relationships) to Neo4j
as a graph for lineage visualization.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

_driver = None


def get_driver():
    """Get or create a Neo4j driver."""
    global _driver
    if _driver is None:
        try:
            from neo4j import GraphDatabase
            _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            _driver.verify_connectivity()
            logger.info("Connected to Neo4j at %s", NEO4J_URI)
        except Exception as e:
            logger.warning("Neo4j connection failed: %s (lineage features disabled)", e)
            _driver = None
    return _driver


def is_available() -> bool:
    """Check if Neo4j is available."""
    driver = get_driver()
    if driver is None:
        return False
    try:
        driver.verify_connectivity()
        return True
    except Exception:
        return False


def push_schema_to_neo4j(schema: dict[str, Any]) -> dict:
    """
    Push complete schema metadata to Neo4j as a graph.
    Creates Table nodes, Column nodes, and FK relationship edges.
    """
    driver = get_driver()
    if not driver:
        return {"status": "skipped", "reason": "Neo4j not available"}

    stats = {"tables": 0, "columns": 0, "relationships": 0}

    try:
        with driver.session() as session:
            # Clear existing graph
            session.run("MATCH (n) DETACH DELETE n")

            for table_name, table_data in schema.items():
                # Create Table node
                session.run(
                    """
                    CREATE (t:Table {
                        name: $name,
                        schema_name: $schema,
                        row_count: $row_count
                    })
                    """,
                    name=table_name,
                    schema=table_data.get("schema_name", "main"),
                    row_count=table_data.get("row_count", 0),
                )
                stats["tables"] += 1

                # Create Column nodes and link to Table
                for col in table_data.get("columns", []):
                    session.run(
                        """
                        MATCH (t:Table {name: $table_name})
                        CREATE (c:Column {
                            name: $name,
                            data_type: $data_type,
                            nullable: $nullable,
                            is_primary_key: $is_pk,
                            is_foreign_key: $is_fk
                        })
                        CREATE (t)-[:HAS_COLUMN]->(c)
                        """,
                        table_name=table_name,
                        name=col.get("name", ""),
                        data_type=col.get("data_type", "UNKNOWN"),
                        nullable=col.get("nullable", True),
                        is_pk=col.get("is_primary_key", False),
                        is_fk=col.get("is_foreign_key", False),
                    )
                    stats["columns"] += 1

                # Create FK relationships between Tables
                for fk in table_data.get("foreign_keys", []):
                    ref_table = fk.get("ref_table", "")
                    if ref_table:
                        session.run(
                            """
                            MATCH (src:Table {name: $src_table})
                            MATCH (dst:Table {name: $dst_table})
                            CREATE (src)-[:REFERENCES {
                                column: $column,
                                ref_column: $ref_column
                            }]->(dst)
                            """,
                            src_table=table_name,
                            dst_table=ref_table,
                            column=fk.get("column", ""),
                            ref_column=fk.get("ref_column", ""),
                        )
                        stats["relationships"] += 1

        logger.info("Pushed schema to Neo4j: %s", stats)
        return {"status": "ok", **stats}

    except Exception as e:
        logger.error("Failed to push schema to Neo4j: %s", e)
        return {"status": "error", "error": str(e)}


def get_lineage(table_name: str) -> dict:
    """Get lineage graph for a specific table (tables that reference it and tables it references)."""
    driver = get_driver()
    if not driver:
        return {"table": table_name, "upstream": [], "downstream": [], "available": False}

    try:
        with driver.session() as session:
            # Upstream: tables that this table references
            upstream = session.run(
                """
                MATCH (src:Table {name: $name})-[r:REFERENCES]->(dst:Table)
                RETURN dst.name AS table_name, r.column AS column, r.ref_column AS ref_column
                """,
                name=table_name,
            ).data()

            # Downstream: tables that reference this table
            downstream = session.run(
                """
                MATCH (src:Table)-[r:REFERENCES]->(dst:Table {name: $name})
                RETURN src.name AS table_name, r.column AS column, r.ref_column AS ref_column
                """,
                name=table_name,
            ).data()

        return {
            "table": table_name,
            "upstream": upstream,
            "downstream": downstream,
            "available": True,
        }
    except Exception as e:
        return {"table": table_name, "error": str(e), "available": False}


def get_full_graph() -> dict:
    """Get the entire lineage graph as nodes and edges for visualization."""
    driver = get_driver()
    if not driver:
        return {"nodes": [], "edges": [], "available": False}

    try:
        with driver.session() as session:
            # Get all Table nodes
            tables = session.run(
                "MATCH (t:Table) RETURN t.name AS name, t.schema_name AS schema, t.row_count AS row_count"
            ).data()

            # Get all FK edges
            edges = session.run(
                """
                MATCH (src:Table)-[r:REFERENCES]->(dst:Table)
                RETURN src.name AS source, dst.name AS target, r.column AS column, r.ref_column AS ref_column
                """
            ).data()

        nodes = [
            {"id": t["name"], "label": t["name"], "schema": t.get("schema", ""), "row_count": t.get("row_count", 0)}
            for t in tables
        ]

        return {
            "nodes": nodes,
            "edges": [{"source": e["source"], "target": e["target"], "label": f"{e['column']} → {e['ref_column']}"} for e in edges],
            "available": True,
        }
    except Exception as e:
        return {"nodes": [], "edges": [], "error": str(e), "available": False}
