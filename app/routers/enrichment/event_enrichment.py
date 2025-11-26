import time
from fastapi import APIRouter, HTTPException
from app.models.request.person_enrichment import EnrichName, EnrichConfirm, EnrichNamesList
from app.services.enrichment.event_enrichment import  enrich_all_events, enrich_events_with_optional_properties
from app.db.neo4j_repo import get_repo

router = APIRouter()

@router.post("")
def enrich_event():
    """Run the basic enrichment and then the optional-property enrichment for all events."""
    start = time.time()
    basic_results = enrich_all_events()
    optional_results = enrich_events_with_optional_properties()
    elapsed = time.time() - start
    return {
        "done_basic": len(basic_results),
        "done_optional": len(optional_results),
        "basic_results": basic_results,
        "optional_results": optional_results,
        "elapsed_seconds": elapsed,
    }