tes 


requirements.txt:

fastapi
uvicorn
requests
neo4j
python-dotenv
httpx


add .env neo4j credentials


run:

uvicorn app.main:app --reload


tes explore/query:

curl -X POST "http://127.0.0.1:8000/explore/cypher" `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"MATCH (e:Event) RETURN e.name AS name LIMIT 5\"}"


tes infobox:

curl -X GET "http://127.0.0.1:8000/infobox/414" -H "Content-Type: application/json"
