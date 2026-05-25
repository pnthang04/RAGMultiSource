#!/usr/bin/env python3
"""
Check documents in database for test user
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repositories.document_repository import DocumentRepository

async def check_documents():
    repo = DocumentRepository()
    user_id = "usr_3ae12fc0-63ed-4729-a896-df1732a29638"
    
    # Get all documents for this user
    docs = await repo.list_user_documents(user_id)
    
    print(f"📄 Documents for user {user_id}:")
    print(f"   Total: {len(docs)}")
    print()
    
    if docs:
        for i, doc in enumerate(docs, 1):
            print(f"{i}. {doc.get('name', 'N/A')}")
            print(f"   ID: {doc.get('_id', 'N/A')}")
            print(f"   Source Type: {doc.get('source_type', 'N/A')}")
            print(f"   Status: {doc.get('status', 'N/A')}")
            print(f"   Created: {doc.get('created_at', 'N/A')}")
            print()
    else:
        print("❌ No documents found!")
        print()
        print("📝 You need to upload documents first before testing retrieval.")

if __name__ == '__main__':
    asyncio.run(check_documents())
