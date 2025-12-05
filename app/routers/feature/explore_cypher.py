from fastapi import APIRouter, HTTPException
from app.db.neo4j_repo import get_repo
from app.models.request.cypherRequest import CypherQueryRequest
from neo4j.graph import Node, Relationship, Path
import re

router = APIRouter()

FORBIDDEN = [
    "CREATE", "MERGE", "DELETE", "SET", "REMOVE", "DROP", "CALL", "LOAD CSV", "UNWIND"
]

def is_safe_cypher(query: str) -> bool:
    pattern = r"\b(" + "|".join(FORBIDDEN) + r")\b"
    return not re.search(pattern, query, re.IGNORECASE)

def format_value_for_table(value):
    if isinstance(value, Node):
        labels = ":".join(value.labels)
        props = dict(value)
        # Format properties untuk display
        if props:
            props_str = ", ".join([f"{k}: {repr(v)}" for k, v in props.items()])
            return f"(:{labels} {{{props_str}}})"
        return f"(:{labels})"
    elif isinstance(value, Relationship):
        props = dict(value)
        if props:
            props_str = ", ".join([f"{k}: {repr(v)}" for k, v in props.items()])
            return f"[:{value.type} {{{props_str}}}]"
        return f"[:{value.type}]"
    elif isinstance(value, Path):
        # Format path: (start)-[rel]->(end)-[rel2]->(end2)
        path_str = ""
        for i, node in enumerate(value.nodes):
            if i > 0:
                rel = value.relationships[i-1]
                path_str += f"-[:{rel.type}]->"
            path_str += format_value_for_table(node)
        return path_str
    elif isinstance(value, list):
        return [format_value_for_table(item) for item in value]
    elif isinstance(value, dict):
        return {k: format_value_for_table(v) for k, v in value.items()}
    else:
        return value

def extract_graph_data(records):
    nodes = {}
    relationships = []
    node_label_counts = {}
    relationship_type_counts = {}
    
    def process_node(node):
        """Helper to process and add a node"""
        node_id = node.element_id
        if node_id not in nodes:
            labels = list(node.labels)
            nodes[node_id] = {
                "id": node_id,
                "labels": labels,
                "properties": dict(node)
            }
            for label in labels:
                node_label_counts[label] = node_label_counts.get(label, 0) + 1
    
    def process_relationship(rel):
        """Helper to process and add a relationship"""
        rel_id = rel.element_id
        # Check if already added
        if not any(r["id"] == rel_id for r in relationships):
            relationships.append({
                "id": rel_id,
                "type": rel.type,
                "startNode": rel.start_node.element_id,
                "endNode": rel.end_node.element_id,
                "properties": dict(rel)
            })
            relationship_type_counts[rel.type] = relationship_type_counts.get(rel.type, 0) + 1
        
        # Process connected nodes
        process_node(rel.start_node)
        process_node(rel.end_node)
    
    for record in records:
        for key, value in record.items():
            if isinstance(value, Node):
                process_node(value)
                        
            elif isinstance(value, Relationship):
                process_relationship(value)
            
            elif isinstance(value, Path):
                # Extract all nodes and relationships from path
                for node in value.nodes:
                    process_node(node)
                for rel in value.relationships:
                    process_relationship(rel)
    
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
        
        # Table view: format langsung untuk display (siap pakai di FE)
        table = []
        for record in records:
            row = {}
            for key in columns:
                row[key] = format_value_for_table(record[key])
            table.append(row)
        
        return {
            "status": "ok",
            "summary": {
                "query": payload.query,
                "recordCount": len(records),
                "columns": columns
            },
            "graph": graph,
            "table": table
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cypher error: {e}")