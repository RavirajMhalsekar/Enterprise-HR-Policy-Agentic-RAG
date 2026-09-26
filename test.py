from app.services.ingestion import load_file, chunk_documents
from pathlib import Path

doc = load_file(Path("data/sample_kb/company_hr_handbook.md"))
chunks = chunk_documents(doc)


print(len(chunks))