#!/usr/bin/env python3
"""
Script để đọc và hiển thị LangSmith traces từ project
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from langsmith import Client
from langsmith.schemas import Run

# Add backend app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Settings


def get_langsmith_client() -> Client:
    """Khởi tạo LangSmith client"""
    settings = Settings()
    
    if not settings.LANGSMITH_API_KEY:
        raise ValueError(
            "LANGSMITH_API_KEY không được set. "
            "Hãy cài đặt trong .env file hoặc environment variable"
        )
    
    client = Client(
        api_key=settings.LANGSMITH_API_KEY,
        api_url=settings.LANGSMITH_ENDPOINT
    )
    return client


def format_run(run: Run, indent: int = 0) -> str:
    """Format một trace run để hiển thị"""
    prefix = "  " * indent
    output = []
    
    output.append(f"{prefix}ID: {run.id}")
    output.append(f"{prefix}Name: {run.name}")
    output.append(f"{prefix}Run Type: {run.run_type}")
    output.append(f"{prefix}Status: {run.status}")
    
    if run.start_time:
        output.append(f"{prefix}Start Time: {run.start_time}")
    
    if run.end_time:
        duration = (run.end_time - run.start_time).total_seconds()
        output.append(f"{prefix}Duration: {duration:.2f}s")
    
    if run.inputs:
        output.append(f"{prefix}Inputs: {json.dumps(run.inputs, indent=2, ensure_ascii=False)}")
    
    if run.outputs:
        output.append(f"{prefix}Outputs: {json.dumps(run.outputs, indent=2, ensure_ascii=False)}")
    
    if run.error:
        output.append(f"{prefix}Error: {run.error}")
    
    if run.tags:
        output.append(f"{prefix}Tags: {', '.join(run.tags)}")
    
    return "\n".join(output)


def list_traces(
    client: Client,
    project_name: str,
    limit: int = 10,
    run_type: Optional[str] = None,
    hours: int = 24,
) -> None:
    """
    Liệt kê các traces gần đây từ project
    
    Args:
        client: LangSmith client
        project_name: Tên project
        limit: Số traces cần lấy
        run_type: Filter theo run type (e.g., 'chain', 'tool', 'llm')
        hours: Lấy traces từ N giờ trước
    """
    try:
        print(f"\n📊 Lấy traces từ project: {project_name}")
        print(f"   Giới hạn: {limit} traces")
        
        if run_type:
            print(f"   Run type: {run_type}")
        
        if hours:
            print(f"   Trong {hours} giờ gần đây")
        
        # Tính thời gian từ N giờ trước
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Lấy runs từ client
        runs = client.list_runs(
            project_name=project_name,
            run_type=run_type,
            limit=limit,
        )
        
        runs_list = list(runs)
        
        if not runs_list:
            print(f"❌ Không tìm thấy traces nào trong {hours} giờ gần đây")
            return
        
        print(f"\n✅ Tìm thấy {len(runs_list)} traces:\n")
        
        for i, run in enumerate(runs_list, 1):
            print(f"\n{'='*80}")
            print(f"TRACE #{i}")
            print(f"{'='*80}")
            print(format_run(run))
    
    except Exception as e:
        print(f"❌ Lỗi khi lấy traces: {str(e)}")
        raise


def get_trace_details(client: Client, trace_id: str) -> None:
    """Lấy chi tiết của một trace cụ thể"""
    try:
        print(f"\n📋 Chi tiết trace: {trace_id}\n")
        
        run = client.read_run(trace_id)
        
        if not run:
            print(f"❌ Không tìm thấy trace: {trace_id}")
            return
        
        print(format_run(run))
        
        # Hiển thị child runs nếu có
        if hasattr(run, 'child_runs') and run.child_runs:
            print(f"\n\n🔗 Child Runs ({len(run.child_runs)}):")
            for child in run.child_runs:
                print(f"\n{'-'*80}")
                print(format_run(child, indent=1))
    
    except Exception as e:
        print(f"❌ Lỗi khi lấy trace: {str(e)}")
        raise


def search_traces(
    client: Client,
    project_name: str,
    query: str,
    limit: int = 10,
) -> None:
    """Tìm kiếm traces theo keyword"""
    try:
        print(f"\n🔍 Tìm kiếm traces: '{query}'")
        print(f"   Project: {project_name}\n")
        
        # Lấy tất cả runs và filter theo query
        runs = client.list_runs(
            project_name=project_name,
            limit=limit * 5,  # Lấy nhiều hơn để filter
        )
        
        matching_runs = []
        for run in runs:
            # Tìm trong name, inputs, outputs, và error
            search_text = json.dumps({
                'name': run.name,
                'inputs': run.inputs,
                'outputs': run.outputs,
                'error': run.error,
            }, ensure_ascii=False).lower()
            
            if query.lower() in search_text:
                matching_runs.append(run)
                if len(matching_runs) >= limit:
                    break
        
        if not matching_runs:
            print(f"❌ Không tìm thấy traces nào khớp với '{query}'")
            return
        
        print(f"✅ Tìm thấy {len(matching_runs)} traces:\n")
        
        for i, run in enumerate(matching_runs, 1):
            print(f"\n{'='*80}")
            print(f"RESULT #{i}")
            print(f"{'='*80}")
            print(format_run(run))
    
    except Exception as e:
        print(f"❌ Lỗi khi tìm kiếm: {str(e)}")
        raise


def export_traces_to_json(
    client: Client,
    project_name: str,
    output_file: str = "langsmith_traces.json",
    limit: int = 100,
) -> None:
    """Export traces thành JSON file"""
    try:
        print(f"\n💾 Export traces thành {output_file}...")
        
        runs = client.list_runs(
            project_name=project_name,
            limit=limit,
        )
        
        traces_data = []
        for run in runs:
            trace_dict = {
                'id': str(run.id),
                'name': run.name,
                'run_type': run.run_type,
                'status': run.status,
                'start_time': run.start_time.isoformat() if run.start_time else None,
                'end_time': run.end_time.isoformat() if run.end_time else None,
                'inputs': run.inputs,
                'outputs': run.outputs,
                'error': run.error,
                'tags': run.tags or [],
            }
            traces_data.append(trace_dict)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(traces_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Export thành công! Đã lưu {len(traces_data)} traces")
        print(f"   File: {output_file}")
    
    except Exception as e:
        print(f"❌ Lỗi khi export: {str(e)}")
        raise


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Đọc và quản lý LangSmith traces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  # Liệt kê 10 traces gần đây
  python read_langsmith_traces.py list --limit 10

  # Liệt kê traces của LLM calls trong 48 giờ qua
  python read_langsmith_traces.py list --run-type llm --hours 48

  # Lấy chi tiết trace cụ thể
  python read_langsmith_traces.py details <trace_id>

  # Tìm kiếm traces chứa từ khóa
  python read_langsmith_traces.py search --query "error"

  # Export tất cả traces thành JSON
  python read_langsmith_traces.py export --output traces.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='Liệt kê traces gần đây')
    list_parser.add_argument('--limit', type=int, default=10, help='Số traces (mặc định: 10)')
    list_parser.add_argument('--run-type', help='Filter theo run type (chain, tool, llm)')
    list_parser.add_argument('--hours', type=int, default=24, help='Từ N giờ trước (mặc định: 24)')
    
    # Details command
    details_parser = subparsers.add_parser('details', help='Lấy chi tiết trace')
    details_parser.add_argument('trace_id', help='ID của trace')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Tìm kiếm traces')
    search_parser.add_argument('--query', required=True, help='Từ khóa tìm kiếm')
    search_parser.add_argument('--limit', type=int, default=10, help='Số results (mặc định: 10)')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export traces thành JSON')
    export_parser.add_argument('--output', default='langsmith_traces.json', help='Output file')
    export_parser.add_argument('--limit', type=int, default=100, help='Số traces (mặc định: 100)')
    
    args = parser.parse_args()
    
    # Khởi tạo client
    settings = Settings()
    client = get_langsmith_client()
    project_name = settings.LANGSMITH_PROJECT
    
    try:
        if args.command == 'list':
            list_traces(
                client,
                project_name,
                limit=args.limit,
                run_type=args.run_type,
                hours=args.hours,
            )
        elif args.command == 'details':
            get_trace_details(client, args.trace_id)
        elif args.command == 'search':
            search_traces(
                client,
                project_name,
                query=args.query,
                limit=args.limit,
            )
        elif args.command == 'export':
            export_traces_to_json(
                client,
                project_name,
                output_file=args.output,
                limit=args.limit,
            )
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Bị gián đoạn bởi người dùng")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Lỗi: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
