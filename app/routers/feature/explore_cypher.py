from fastapi import APIRouter, HTTPException
from app.db.neo4j_repo import get_repo
from app.models.request.cypherRequest import CypherQueryRequest
from neo4j.graph import Node, Relationship
import re

router = APIRouter()

FORBIDDEN = [
    "CREATE", "MERGE", "DELETE", "SET", "REMOVE", "DROP", "CALL", "LOAD CSV", "UNWIND"
]

def is_safe_cypher(query: str) -> bool:
    pattern = r"\b(" + "|".join(FORBIDDEN) + r")\b"
    return not re.search(pattern, query, re.IGNORECASE)

def serialize_neo4j_value(value):
    """
    Convert Neo4j types to JSON-serializable format.
    """
    if isinstance(value, Node):
        return {
            "identity": value.element_id,
            "labels": list(value.labels),
            "properties": dict(value),
            "elementType": "node"
        }
    elif isinstance(value, Relationship):
        return {
            "identity": value.element_id,
            "type": value.type,
            "start": value.start_node.element_id,
            "end": value.end_node.element_id,
            "properties": dict(value),
            "elementType": "relationship"
        }
    elif isinstance(value, list):
        return [serialize_neo4j_value(item) for item in value]
    elif isinstance(value, dict):
        return {k: serialize_neo4j_value(v) for k, v in value.items()}
    else:
        return value

def extract_graph_data(records):
    """
    Extract nodes and relationships from Neo4j records for graph visualization.
    Compatible with Neo4j Browser format with statistics.
    """
    nodes = {}
    relationships = []
    node_label_counts = {}
    relationship_type_counts = {}
    
    for record in records:
        for key, value in record.items():
            if isinstance(value, Node):
                node_id = value.element_id
                if node_id not in nodes:
                    labels = list(value.labels)
                    nodes[node_id] = {
                        "id": node_id,
                        "labels": labels,
                        "properties": dict(value)
                    }
                    # Count node labels
                    for label in labels:
                        node_label_counts[label] = node_label_counts.get(label, 0) + 1
                        
            elif isinstance(value, Relationship):
                rel_id = value.element_id
                start_id = value.start_node.element_id
                end_id = value.end_node.element_id
                rel_type = value.type
                
                relationships.append({
                    "id": rel_id,
                    "type": rel_type,
                    "startNode": start_id,
                    "endNode": end_id,
                    "properties": dict(value)
                })
                
                # Count relationship types
                relationship_type_counts[rel_type] = relationship_type_counts.get(rel_type, 0) + 1
                
                # Add related nodes if not already added
                if start_id not in nodes:
                    start_labels = list(value.start_node.labels)
                    nodes[start_id] = {
                        "id": start_id,
                        "labels": start_labels,
                        "properties": dict(value.start_node)
                    }
                    for label in start_labels:
                        node_label_counts[label] = node_label_counts.get(label, 0) + 1
                        
                if end_id not in nodes:
                    end_labels = list(value.end_node.labels)
                    nodes[end_id] = {
                        "id": end_id,
                        "labels": end_labels,
                        "properties": dict(value.end_node)
                    }
                    for label in end_labels:
                        node_label_counts[label] = node_label_counts.get(label, 0) + 1
    
    return {
        "nodes": list(nodes.values()),
        "relationships": relationships,
        "stats": {
            "nodeCount": len(nodes),
            "relationshipCount": len(relationships),
            "nodeLabels": node_label_counts,
            "relationshipTypes": relationship_type_counts
        }
    }

@router.post("/explore/cypher")
def run_cypher_query(payload: CypherQueryRequest):
    """
    Jalankan Cypher query custom dari user ke Neo4j.
    Hanya untuk eksplorasi data (tidak boleh mengubah DB).
    Returns data in Neo4j Browser compatible format for Graph, Table, and Text views.
    """
    if not is_safe_cypher(payload.query):
        raise HTTPException(
            status_code=403,
            detail="Forbidden Cypher command detected! Only read-only queries (MATCH/RETURN) are allowed."
        )
    
    repo = get_repo()
    
    def execute_query():
        with repo.driver.session(database=repo.db) as session:
            result = session.run(payload.query)
            records = list(result)
            columns = result.keys() if records else []
            return records, columns
    
    try:
        # Execute with automatic retry on connection failures
        records, columns = repo.execute_with_retry(execute_query)
        
        # Extract graph data (nodes and relationships)
        graph = extract_graph_data(records)
        
        # Table view: structured data with serialized Neo4j objects
        table = []
        for record in records:
            row = {}
            for key in columns:
                row[key] = serialize_neo4j_value(record[key])
            table.append(row)
        
        # Text/Raw view: simple key-value pairs
        text = []
        for i, record in enumerate(records):
            row_data = {}
            for key in columns:
                value = record[key]
                if isinstance(value, Node):
                    row_data[key] = f"(:{''.join(value.labels)} {dict(value)})"
                elif isinstance(value, Relationship):
                    row_data[key] = f"[:{value.type} {dict(value)}]"
                else:
                    row_data[key] = value
            text.append(row_data)
        
        return {
            "status": "ok",
            "summary": {
                "query": payload.query,
                "recordCount": len(records),
                "columns": columns
            },
            "graph": graph,
            "table": table,
            "text": text
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cypher error: {e}")