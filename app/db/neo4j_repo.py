# neo4j_repo.py
import os
import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD")
NEO4J_DB   = os.getenv("NEO4J_DATABASE", "neo4j")

AURA_INSTANCEID = os.getenv("AURA_INSTANCEID")
AURA_INSTANCENAME = os.getenv("AURA_INSTANCENAME")

# Connection pool configuration for production
driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASS),
    max_connection_lifetime=3600,  # 1 hour
    max_connection_pool_size=50,
    connection_acquisition_timeout=60,
    keep_alive=True,
    connection_timeout=30
)

class Neo4jRepo:
    def __init__(self, driver):
        self.driver = driver
        self.db = NEO4J_DB
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    def execute_with_retry(self, query_func, *args, **kwargs):
        """
        Execute query with automatic retry on connection failures.
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return query_func(*args, **kwargs)
            except (ServiceUnavailable, SessionExpired) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.warning(
                        f"Neo4j connection failed (attempt {attempt + 1}/{self.max_retries}). "
                        f"Retrying in {wait_time}s... Error: {str(e)}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Neo4j connection failed after {self.max_retries} attempts: {str(e)}")
        
        raise last_exception

    def verify_connectivity(self):
        """
        Verify connection to Neo4j database.
        """
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j connectivity check failed: {str(e)}")
            return False

    def close(self):
        self.driver.close()

def get_repo():
    return Neo4jRepo(driver)