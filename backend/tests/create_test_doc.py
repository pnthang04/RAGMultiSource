#!/usr/bin/env python3
"""
Create a test document for the user by cloning a system document
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repositories.document_repository import DocumentRepository
from app.models.document import DocumentModel
from app.utils.id_utils import generate_id

async def create_test_document():
    repo = DocumentRepository()
    user_id = "usr_3ae12fc0-63ed-4729-a896-df1732a29638"
    
    # Get a system document to use as template
    system_docs = await repo.list_system_ready_documents()
    
    if not system_docs:
        print("❌ No system documents found!")
        return
    
    template_doc = system_docs[0]
    
    # Create new document for user
    new_doc = DocumentModel(
        _id=generate_id("doc"),
        title=f"Test Document - {template_doc.get('name', 'System Doc')}",
        filename=template_doc.get('filename', 'test.pdf') or 'test.pdf',
        file_type=template_doc.get('file_type', 'pdf') or 'pdf',
        mime_type=template_doc.get('mime_type', 'application/pdf') or 'application/pdf',
        source_type="user_upload",
        visibility="private",
        owner_user_id=user_id,
        uploaded_in_session_id=None,
        procedure_title=template_doc.get('procedure_title'),
        status="ready",
        raw_storage_path=template_doc.get('raw_storage_path', 'storage/raw/test.pdf') or 'storage/raw/test.pdf',
        markdown_storage_path=template_doc.get('markdown_storage_path'),
        page_count=template_doc.get('page_count', 1),
        page_source=template_doc.get('page_source'),
        chunk_count=template_doc.get('chunk_count', 0),
        file_size_bytes=template_doc.get('file_size_bytes', 0),
        content_hash=template_doc.get('content_hash'),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    # Create the document
    doc_id = await repo.create_document(new_doc)
    
    print("✅ Test document created!")
    print(f"   Document ID: {doc_id}")
    print(f"   Title: {new_doc.title}")
    print(f"   Owner: {user_id}")
    print()
    print("📝 Note: This is a reference to system document data.")
    print("   The chunks will come from the system document's markdown path.")
    
    return doc_id

if __name__ == '__main__':
    asyncio.run(create_test_document())
