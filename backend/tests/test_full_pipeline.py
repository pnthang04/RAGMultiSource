#!/usr/bin/env python3
"""
Test full RAG pipeline with trace analysis
"""
import requests
import json
import time

def test_pipeline():
    query = 'file tuần trước tôi up lên có lệ phí dăng kí là bao nhiêu đi bạn'
    token = 'oMSHHGeNtc7NLBg3Bh1cgPWqCbDlG3ki5BATdCYT7eI'
    
    payload = {
        'question': query,
        'scope': 'system_docs'
    }
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print('🚀 Sending query to RAG pipeline...')
    print(f'Query: {query}')
    print('-' * 80)
    
    response = requests.post('http://127.0.0.1:8000/chat', json=payload, headers=headers)
    print(f'Status: {response.status_code}')
    print()
    
    result = response.json()
    print('Response:')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Extract useful info
    print('\n' + '=' * 80)
    print('📊 Pipeline Results:')
    print('=' * 80)
    
    if 'answer' in result:
        print(f'\n✅ Answer:\n{result["answer"]}\n')
    
    if 'raw_contexts' in result:
        chunks = result['raw_contexts']
        print(f'\n📚 Retrieved Chunks: {len(chunks)} chunks')
        for i, chunk in enumerate(chunks, 1):
            print(f'\n  Chunk {i}:')
            if isinstance(chunk, dict):
                print(f'    Content: {str(chunk)[:200]}...')
    
    if 'trace_id' in result:
        print(f'\n🔗 Trace ID: {result["trace_id"]}')
    
    return result

if __name__ == '__main__':
    test_pipeline()
