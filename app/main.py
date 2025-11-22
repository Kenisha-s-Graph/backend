# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.services.enrich_service import enrich_person_by_name
from app.db.neo4j_repo import get_repo
import time

app = FastAPI(title="KG Enrichment Service - Person")

class EnrichName(BaseModel):
    name: str

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/enrich/person")
def enrich_person(payload: EnrichName):
    res = enrich_person_by_name(payload.name)
    if res.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"Person {payload.name} not found in internal DB")
    if res.get("status") == "qid_not_found":
        raise HTTPException(status_code=404, detail=f"Wikidata QID not found for {payload.name}")
    return res

@app.post("/enrich/persons/batch")
def enrich_batch(offset: int = 0, limit: int = 100):
    repo = get_repo()
    # Query hanya person yang belum punya MEMBER_OF_DYNASTY
    with repo.driver.session(database=repo.db) as session:
        res = session.run("""
            MATCH (p:Person)
            WHERE NOT (p)-[:MEMBER_OF_DYNASTY]->(:Dynasty)
            RETURN p.name AS name, p.article_id AS article_id, p.full_name AS full_name
            SKIP $offset LIMIT $limit
        """, {"offset": offset, "limit": limit})
        persons = [dict(r) for r in res]
    results = []
    for p in persons:
        name = p.get('full_name')
        if not name:
            continue
        try:
            r = enrich_person_by_name(name)
            results.append({name: r})
        except Exception as e:
            results.append({name: {"status":"error", "error": str(e)}})
        time.sleep(0.5)
    return {"done": len(results), "results": results}