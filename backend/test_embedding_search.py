#!/usr/bin/env python3
"""
Test embedding search trong vector database
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.embedding.bge_embedding import BGEEmbeddingService
from app.rag.vectorstore.chroma_store import ChromaVectorStore
import json


def test_embedding_search():
    """Test embedding search"""
    query = "lệ phí khi cấp lại thông báo văn bản bưu chính có lệ phí là bao nhiêu thế bạn"
    
    print(f"🔍 Query: {query}\n")
    
    # Init services
    embedding_service = BGEEmbeddingService()
    vector_store = ChromaVectorStore()
    
    # Embed query
    print("⏳ Embedding query...")
    query_embedding = embedding_service.embed_text(query)
    print(f"✅ Embedding done. Dimension: {len(query_embedding)}\n")
    
    # Test 1: Search WITHOUT metadata filter
    print("=" * 80)
    print("TEST 1: Search WITHOUT metadata filter")
    print("=" * 80)
    
    results_no_filter = vector_store.search(
        query_embedding=query_embedding,
        where_filter=None,
        top_k=5
    )
    
    print(f"✅ Found {len(results_no_filter)} chunks\n")
    
    for i, chunk in enumerate(results_no_filter, 1):
        print(f"\n--- Chunk {i} ---")
        print(f"ID: {chunk['id']}")
        print(f"Similarity: {chunk['similarity']:.4f}")
        print(f"Metadata: {json.dumps(chunk['metadata'], indent=2, ensure_ascii=False)}")
        print(f"Content: {chunk['content'][:200]}...")
    
    # Test 2: Search WITH loose filter (only source_type)
    print("\n\n" + "=" * 80)
    print("TEST 2: Search WITH loose filter (source_type=system only)")
    print("=" * 80)
    
    loose_filter = {"source_type": "system"}
    results_loose = vector_store.search(
        query_embedding=query_embedding,
        where_filter=loose_filter,
        top_k=5
    )
    
    print(f"✅ Found {len(results_loose)} chunks\n")
    
    for i, chunk in enumerate(results_loose, 1):
        print(f"\n--- Chunk {i} ---")
        print(f"ID: {chunk['id']}")
        print(f"Similarity: {chunk['similarity']:.4f}")
        print(f"Metadata: {json.dumps(chunk['metadata'], indent=2, ensure_ascii=False)}")
        print(f"Content: {chunk['content'][:200]}...")
    
    # Test 3: Search WITH strict filter (procedure_title=procedure/fee)
    print("\n\n" + "=" * 80)
    print("TEST 3: Search WITH strict filter (procedure_title=procedure/fee)")
    print("=" * 80)
    
    strict_filter = {
        "$and": [
            {"source_type": "system"},
            {"visibility": "global"},
            {"procedure_title": "procedure/fee"}
        ]
    }
    
    results_strict = vector_store.search(
        query_embedding=query_embedding,
        where_filter=strict_filter,
        top_k=5
    )
    
    print(f"✅ Found {len(results_strict)} chunks\n")
    
    if not results_strict:
        print("❌ No chunks found with strict filter!")
    else:
        for i, chunk in enumerate(results_strict, 1):
            print(f"\n--- Chunk {i} ---")
            print(f"ID: {chunk['id']}")
            print(f"Similarity: {chunk['similarity']:.4f}")
            print(f"Metadata: {json.dumps(chunk['metadata'], indent=2, ensure_ascii=False)}")
            print(f"Content: {chunk['content'][:200]}...")
    
    # Summary
    print("\n\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"No filter: {len(results_no_filter)} chunks")
    print(f"Loose filter (source_type=system): {len(results_loose)} chunks")
    print(f"Strict filter (procedure_title=procedure/fee): {len(results_strict)} chunks")
    print("\n✅ Conclusion: Loose filter works! Skip procedure_title exact match!")


if __name__ == "__main__":
    test_embedding_search()
