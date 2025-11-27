from fastapi import APIRouter, HTTPException, Query
from app.db.neo4j_repo import get_repo
from pydantic import BaseModel
from typing import Optional, List
import re

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 20
    current_person_count: int = 0
    current_event_count: int = 0
    search_type: Optional[str] = "all"  # "person", "event", "all"
    filter_country: Optional[List[str]] = None 
    filter_continent: Optional[List[str]] = None 

@router.post("/search")
def search_historical_data(payload: SearchRequest):
    """
    Universal search untuk Historical Person & Events
    Mencari berdasarkan nama, deskripsi, dan konteks terkait
    """
    if len(payload.query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query minimal 2 karakter")
    
    repo = get_repo()
    query_lower = payload.query.lower().strip()
    
    results = {
        "query": payload.query,
        "persons": {
            "data": [],
            "total_found": 0
        },
        "events": {
            "data": [],
            "total_found": 0
        }
    }

    def _build_filter_conditions():
        """Build filter conditions and return WHERE clauses with parameters"""
        filter_conditions = []
        params = {"query": query_lower}
        
        # Country filter - support multiple countries
        if payload.filter_country and len(payload.filter_country) > 0:
            country_list = [c.lower() for c in payload.filter_country]
            filter_conditions.append("toLower(country.country) IN $filter_countries")
            params["filter_countries"] = country_list
        
        # Continent filter - support multiple continents  
        if payload.filter_continent and len(payload.filter_continent) > 0:
            continent_list = [c.lower() for c in payload.filter_continent]
            filter_conditions.append("toLower(continent.continent) IN $filter_continents")
            params["filter_continents"] = continent_list
            
        return filter_conditions, params
    
    try:
        with repo.driver.session(database=repo.db) as session:
            
            filter_conditions, base_params = _build_filter_conditions()

            # PERSON SEARCH - Multi-field search
            if payload.search_type in ["person", "all"]:

                # Build main search conditions (always these, no country/continent search here)
                search_conditions = [
                    "toLower(p.full_name) CONTAINS $query",
                    "toLower(p.description) CONTAINS $query", 
                    "toLower(pos.label) CONTAINS $query",
                    "toLower(pos.name) CONTAINS $query"
                ]
                
                # Build WHERE statement
                where_statement = "WHERE (" + " OR ".join(search_conditions) + ")"
                
                # Add filter conditions with AND logic (separate from search conditions)
                if filter_conditions:
                    filter_where = " AND (" + " AND ".join(filter_conditions) + ")"
                    where_statement += filter_where

                person_cypher = f"""
                MATCH (p:Person)
                OPTIONAL MATCH (p)-[:HELD_POSITION]->(pos:Position)  
                OPTIONAL MATCH (p)-[:BORN_IN]->(c:City)-[:LOCATED_IN]->(country:Country)-[:LOCATED_IN]->(continent:Continent)
                { where_statement }
                WITH DISTINCT p, pos, country, continent
                RETURN 
                    id(p) AS id,
                    p.full_name AS name,
                    p.description AS description,
                    p.image_url AS image,
                    coalesce(pos.label, pos.name) AS position,
                    country.country AS country
                SKIP $offset
                LIMIT $limit
                """
                
                person_params = base_params.copy()
                person_params.update({
                    "limit": payload.limit,
                    "offset": payload.current_person_count
                })
                
                person_results = session.run(person_cypher, person_params)
                
                for record in person_results:
                    results["persons"]["data"].append({
                        "type": "person",
                        "id": record["id"],
                        "name": record["name"],
                        "description": record["description"],
                        "image": record["image"],
                        "context": {
                            "position": record["position"], 
                            "country": record["country"]
                        }
                    })
            
            person_found = len(results["persons"]["data"])
            results["persons"]["total_found"] = person_found

            event_limit = payload.limit - person_found

            # EVENT SEARCH - Multi-field search  
            if (event_limit > 0) and (payload.search_type in ["event", "all"]):
                
                # Build main search conditions for events (no country/continent search here)
                search_conditions = [
                    "toLower(e.name) CONTAINS $query",
                    "toLower(e.description) CONTAINS $query",
                    "toLower(e.impact) CONTAINS $query"
                ]
                
                # Build WHERE statement
                where_statement = "WHERE (" + " OR ".join(search_conditions) + ")"
                
                # Add filter conditions with AND logic (separate from search conditions)
                if filter_conditions:
                    filter_where = " AND (" + " AND ".join(filter_conditions) + ")"
                    where_statement += filter_where

                event_cypher = f"""
                MATCH (e:Event)
                OPTIONAL MATCH (e)-[:HELD_IN]->(country:Country)-[:LOCATED_IN]->(continent:Continent)
                { where_statement }
                WITH DISTINCT e, country, continent
                RETURN 
                    id(e) AS id,
                    e.name AS name,
                    e.description AS description, 
                    e.image_url AS image,
                    e.impact AS impact,
                    country.country AS country
                SKIP $offset
                LIMIT $limit
                """
                
                event_params = base_params.copy()
                event_params.update({
                    "limit": event_limit,
                    "offset": payload.current_event_count
                })
                
                event_results = session.run(event_cypher, event_params)
                                
                for record in event_results:
                    results["events"]["data"].append({
                        "type": "event", 
                        "id": record["id"],
                        "name": record["name"],
                        "description": record["description"],
                        "image": record["image"], 
                        "context": {
                            "country": record["country"],
                            "impact": record["impact"]
                        }
                    })
                
            event_found = len(results["events"]["data"])
            results["events"]["total_found"] = event_found
            
            return results
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/search/filters")
def get_available_filters():
    """
    Get available filter options (countries, continents)
    """
    repo = get_repo()
    
    try:
        with repo.driver.session(database=repo.db) as session:
            
            # Get countries
            countries_cypher = """
            MATCH (c:Country)
            RETURN DISTINCT c.country AS name
            ORDER BY name
            """
            
            countries = []
            for record in session.run(countries_cypher):
                if record["name"]:  # Skip null values
                    countries.append(record["name"])
            
            # Get continents  
            continents_cypher = """
            MATCH (cont:Continent)
            RETURN DISTINCT cont.continent AS name
            ORDER BY name
            """
            
            continents = []
            for record in session.run(continents_cypher):
                if record["name"]:  # Skip null values
                    continents.append(record["name"])
            
            return {
                "countries": countries,
                "continents": continents
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Filters error: {str(e)}")

@router.get("/search/suggestions")
def get_search_suggestions(q: str = Query(..., min_length=2)):
    """
    Auto-complete suggestions untuk search
    """
    repo = get_repo()
    
    try:
        with repo.driver.session(database=repo.db) as session:
            suggestions_cypher = """
            MATCH (p:Person)
            WHERE toLower(p.full_name) STARTS WITH $query
            RETURN p.full_name AS suggestion, "person" AS type
            LIMIT 5
            
            UNION
            
            MATCH (e:Event)
            WHERE toLower(e.name) STARTS WITH $query
            RETURN e.name AS suggestion, "event" AS type
            LIMIT 5
            """
            
            results = session.run(suggestions_cypher, {"query": q.lower()})
            
            suggestions = []
            for record in results:
                suggestions.append({
                    "text": record["suggestion"],
                    "type": record["type"] 
                })
            
            return {"suggestions": suggestions}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestions error: {str(e)}")