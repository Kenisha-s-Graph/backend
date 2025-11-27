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


Example explore/query:

curl -X POST "http://127.0.0.1:8000/explore/cypher" `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"MATCH (q:Person) RETURN q AS person LIMIT 1\"}"

response:

{
  "status": "ok",
  "results": [
    {
      "person": {
        "cause_of_death": "myocardial infarction",
        "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Poet%20Ted%20HughesDCP%202068.JPG",
        "sex": "Male",
        "description": "English poet and children's writer (1930-1998)",
        "wikidata_qid": "Q272194",
        "abstract": "English poet and children's writer (1930-1998)",
        "birth_year": 1930,
        "death_date": "1998-10-28T00:00:00Z",
        "article_id": 31034,
        "historical_popularity_index": 21.388,
        "full_name": "Ted Hughes",
        "average_views": 76462,
        "page_views": 2370318,
        "death_place": "London",
        "article_languages": 31
      }
    }
  ]
}



Example infobox:

curl -X GET "http://127.0.0.1:8000/infobox/4:9fab8707-88a2-4b92-b1de-cd98b985884e:17891" -H "Content-Type: application/json"

response: 

{
  "status": "ok",
  "element_id": "4:9fab8707-88a2-4b92-b1de-cd98b985884e:17891",
  "labels": ["Event"],
  "properties": {
    "name": "World Economic Forum Annual Meeting 2018"
  },
  "related_nodes": [
    {
      "element_id": "4:9fab8707-88a2-4b92-b1de-cd98b985884e:32",
      "relationship": "PARTICIPATED_IN",
      "labels": ["Person"],
      "properties": {
        "article_id": 142550,
        "historical_popularity_index": 21.3378,
        "full_name": "Yo-Yo Ma",
        "average_views": 99602,
        "page_views": 3386451,
        "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Yo-Yo%20Ma%20in%202018%20%28cropped%29.jpg",
        "sex": "Male",
        "description": "American cellist (born 1955)",
        "wikidata_qid": "Q234891",
        "abstract": "American cellist (born 1955)",
        "article_languages": 34,
        "birth_year": 1955
      }
    },
    {
      "element_id": "4:9fab8707-88a2-4b92-b1de-cd98b985884e:99",
      "relationship": "PARTICIPATED_IN",
      "labels": ["Person"],
      "properties": {
        "article_id": 9743046,
        "historical_popularity_index": 21.2497,
        "full_name": "Juan Manuel Santos",
        "average_views": 49184,
        "page_views": 2213294,
        "image_url": "http://commons.wikimedia.org/wiki/Special:FilePath/Juan%20Manuel%20Santos%20and%20Lula%20%28cropped%29.jpg",
        "sex": "Male",
        "description": "former president of Colombia from 2010 to 2018",
        "wikidata_qid": "Q57311",
        "abstract": "former president of Colombia from 2010 to 2018",
        "article_languages": 45,
        "birth_year": 1951
      }
    }
  ]
}