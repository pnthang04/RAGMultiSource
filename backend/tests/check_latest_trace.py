#!/usr/bin/env python3
"""
Get the latest trace to debug the pipeline
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scripts.read_langsmith_traces import list_traces

# Get latest trace
traces = list_traces(limit=5, hours=1)

if traces:
    print('🔍 Latest Traces:')
    print('=' * 80)
    for i, trace in enumerate(traces[:3], 1):
        print(f'\n{i}. {trace.get("name", "N/A")}')
        print(f'   Run ID: {trace.get("id", "N/A")}')
        print(f'   Status: {trace.get("status", "N/A")}')
        print(f'   Created: {trace.get("created_at", "N/A")}')
        
        # Show input
        if 'inputs' in trace:
            inputs = trace['inputs']
            if isinstance(inputs, dict):
                if 'question' in inputs:
                    print(f'   Question: {inputs["question"][:80]}...')
        
        # Show output
        if 'outputs' in trace:
            outputs = trace['outputs']
            if isinstance(outputs, dict):
                if 'answer' in outputs:
                    print(f'   Answer: {outputs["answer"][:80]}...')
        
        print(f'   Run Type: {trace.get("run_type", "N/A")}')
else:
    print('No traces found')
