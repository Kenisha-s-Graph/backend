import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD")
NEO4J_DB   = os.getenv("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASS)
)

class EventRepo:
    def __init__(self, driver):
        self.driver = driver
        self.db = NEO4J_DB

    def get_all_events(self, limit=1000):
        with self.driver.session(database=self.db) as session:
            res = session.run("""
                MATCH (e:Event)
                RETURN e.name AS name, e.event_id AS event_id
                LIMIT $limit
            """, {"limit": limit})
            return [dict(r) for r in res]

    def upsert_event_enrichment(
        self,
        event_id,
        qid,
        description=None,
        image=None
    ):
        with self.driver.session(database=self.db) as session:

            # Update basic attributes
            session.run("""
                MATCH (e:Event {event_id: $event_id})
                SET e.wikidata_qid = $qid,
                    e.description = $description,
                    e.image_url = $image
            """, {
                "event_id": event_id,
                "qid": qid,
                "description": description,
                "image": image
            })


def get_event_repo():
    return EventRepo(driver)