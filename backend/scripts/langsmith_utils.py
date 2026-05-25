#!/usr/bin/env python3
"""
Quick utilities để làm việc với LangSmith traces
Sử dụng script này để nhanh chóng analyze traces
"""

import json
import sys
from pathlib import Path
from datetime import datetime

from read_langsmith_traces import get_langsmith_client, Settings


def print_section(title: str):
    """In section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def analyze_traces_json(json_file: str) -> None:
    """Phân tích traces từ JSON file"""
    print_section(f"Phân tích: {json_file}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            traces = json.load(f)
        
        print(f"\n📊 Tổng số traces: {len(traces)}")
        
        # Thống kê theo run type
        run_types = {}
        statuses = {}
        total_duration = 0
        errors = []
        
        for trace in traces:
            # Count by run type
            run_type = trace.get('run_type', 'unknown')
            run_types[run_type] = run_types.get(run_type, 0) + 1
            
            # Count by status
            status = trace.get('status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1
            
            # Calculate duration
            start = trace.get('start_time')
            end = trace.get('end_time')
            if start and end:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                duration = (end_dt - start_dt).total_seconds()
                total_duration += duration
            
            # Collect errors
            if trace.get('error'):
                errors.append({
                    'id': trace.get('id'),
                    'name': trace.get('name'),
                    'error': trace.get('error')[:100]  # First 100 chars
                })
        
        # Print stats
        print("\n📈 Thống kê Run Type:")
        for run_type, count in sorted(run_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {run_type}: {count}")
        
        print("\n✅ Thống kê Status:")
        for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
            print(f"   {status}: {count}")
        
        print(f"\n⏱️  Tổng thời gian thực thi: {total_duration:.2f}s")
        if traces:
            print(f"   Trung bình: {total_duration/len(traces):.2f}s per trace")
        
        if errors:
            print(f"\n❌ Traces có lỗi ({len(errors)}):")
            for err in errors[:10]:  # Show first 10
                print(f"   [{err['id'][:8]}...] {err['name']}: {err['error']}")
            if len(errors) > 10:
                print(f"   ... và {len(errors) - 10} lỗi khác")
        else:
            print(f"\n✅ Không có lỗi!")
    
    except FileNotFoundError:
        print(f"❌ File không tìm thấy: {json_file}")
    except json.JSONDecodeError:
        print(f"❌ File JSON không hợp lệ: {json_file}")
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")


def quick_stats() -> None:
    """In quick statistics về project"""
    print_section("LangSmith Project Statistics")
    
    try:
        settings = Settings()
        client = get_langsmith_client()
        
        print(f"\n🔗 Project: {settings.LANGSMITH_PROJECT}")
        print(f"🌐 Endpoint: {settings.LANGSMITH_ENDPOINT}")
        
        # Get recent traces
        runs = list(client.list_runs(
            project_name=settings.LANGSMITH_PROJECT,
            limit=100,
        ))
        
        if not runs:
            print(f"❌ Không có traces trong project")
            return
        
        # Count by type
        by_type = {}
        by_status = {}
        
        for run in runs:
            by_type[run.run_type] = by_type.get(run.run_type, 0) + 1
            by_status[run.status] = by_status.get(run.status, 0) + 1
        
        print(f"\n📊 Trong 100 traces gần nhất:")
        print(f"   Total: {len(runs)}")
        
        print(f"\n   Run Types:")
        for t, c in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"      {t}: {c}")
        
        print(f"\n   Statuses:")
        for s, c in sorted(by_status.items(), key=lambda x: x[1], reverse=True):
            print(f"      {s}: {c}")
        
        # Find failed ones
        failed = [r for r in runs if r.status == 'error']
        if failed:
            print(f"\n   ❌ Lỗi gần đây:")
            for run in failed[:5]:
                print(f"      - {run.name}: {run.error[:50] if run.error else 'No error msg'}")
    
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")


def main():
    """Main"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LangSmith Traces Utilities",
        epilog="""
Ví dụ:
  python langsmith_utils.py stats              # Xem statistics
  python langsmith_utils.py analyze traces.json # Phân tích JSON file
        """
    )
    
    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('stats', help='Xem statistics')
    
    analyze_parser = subparsers.add_parser('analyze', help='Phân tích JSON file')
    analyze_parser.add_argument('file', help='JSON file path')
    
    args = parser.parse_args()
    
    if args.command == 'stats':
        quick_stats()
    elif args.command == 'analyze':
        analyze_traces_json(args.file)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
