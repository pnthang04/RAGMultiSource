#!/usr/bin/env python3
"""
Update created user documents to source_type=system for testing retrieval
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repositories.document_repository import DocumentRepository

async def update_docs():
    repo = DocumentRepository()
    user_id = "usr_3ae12fc0-63ed-4729-a896-df1732a29638"
    docs = await repo.list_user_documents(user_id)
    if not docs:
        print('No user docs found')
        return
    for doc in docs:
        doc_id = doc.get('_id')
        print(f'Updating {doc_id} -> source_type=system, owner_user_id=None, visibility=global')
        await repo.update_document_fields(doc_id, source_type='system', owner_user_id=None, visibility='global')
    print('Done')

if __name__ == '__main__':
    asyncio.run(update_docs())
