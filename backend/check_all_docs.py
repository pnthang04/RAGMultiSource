#!/usr/bin/env python3
"""
Check system documents and user documents
"""
import asyncio
import sys
sys.path.insert(0, 'd:\\Project\\Chatbot\\backend')

from app.repositories.document_repository import DocumentRepository

async def check_all_documents():
    repo = DocumentRepository()
    
    # Check system documents
    system_docs = await repo.list_system_ready_documents()
    print(f"📚 System Documents: {len(system_docs)}")
    if system_docs:
        for i, doc in enumerate(system_docs[:3], 1):
            print(f"   {i}. {doc.get('name', 'N/A')[:50]}")
    
    print()
    
    # Check all user documents
    all_user_docs = await repo.list_documents(owner_user_id=None)
    print(f"👤 All User Uploads: {len(all_user_docs)}")
    if all_user_docs:
        for i, doc in enumerate(all_user_docs[:3], 1):
            print(f"   {i}. {doc.get('name', 'N/A')[:50]}")
            print(f"      Owner: {doc.get('owner_user_id', 'N/A')}")

if __name__ == '__main__':
    asyncio.run(check_all_documents())
