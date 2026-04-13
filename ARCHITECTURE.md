# Architecture Notes

## Week 1

Retrieval is a combination of dense vector search and BM25 (RRF + reranker) since the product spec sheets require both semantic matching and literal keyword matching. The payload filtering done by Qdrant ensures that each agent processes only one document's chunks at a time, avoiding any mixing of information between products. The use of `pdfplumber` retains any table as markdown, while the use of `RecursiveCharacterTextSplitter` ensures the continuity of attribute groups within chunks. `instructor` ensures that the returned JSON is validated using Pydantic with retries for all Claude API calls.

## Week 2


## Week 3