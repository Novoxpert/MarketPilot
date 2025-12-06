"""
Enhanced Marketpilot Data Farm Pipeline CLI
============================================

Features:
- Real-time stage progress with detailed metrics
- Rich data visualization for each stage
- Interactive data preview after each stage
- Summary statistics and quality metrics
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.padding import Padding
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.tree import Tree
from rich.syntax import Syntax
import json

from marketpilot.data_farm.resilient_data_farm import ResilientDataFarm

console = Console()

# Stage configuration
STAGE_CONFIG = {
    "health_check": {
        "name": "Health Check",
        "data_keys": ["health_check"],
        "metrics": ["overall_status", "apis_healthy", "apis_checked"],
    },
    "data_collection": {
        "name": "Data Collection",
        "data_keys": ["raw_data", "collection_summary"],
        "metrics": ["total_records", "successful", "failed"],
    },
    "nan_processing": {
        "name": "NaN Processing",
        "data_keys": ["processed_data", "nan_stats"],
        "metrics": ["nan_count"],
    },
    "temporal_alignment": {
        "name": "Temporal Alignment",
        "data_keys": ["aligned_data", "alignment_stats"],
        "metrics": ["aligned_count", "failed_count", "alignment_rate"],
    },
    "deduplication": {
        "name": "Deduplication",
        "data_keys": ["unique_data", "dedup_stats"],
        "metrics": ["duplicates_removed", "unique_records", "duplicate_rate"],
    },
    "quality_assurance": {
        "name": "Quality Assurance",
        "data_keys": ["validated_data", "qa_stats"],
        "metrics": ["qa_passed", "qa_failed", "pass_rate", "threshold_met"],
    },
    "data_export": {
        "name": "Data Export",
        "data_keys": ["export_stats"],
        "metrics": ["records_exported", "files_created", "output_directory"],
    },
}


def parse_symbols(input_str: str) -> List[str]:
    """Parse comma-separated symbols input."""
    if not input_str or input_str.strip().lower() == "none":
        return ["BINANCE:BTCUSDT.P", "BINANCE:ETHUSDT.P"]
    
    symbols = [s.strip() for s in input_str.split(",") if s.strip()]
    return symbols


def parse_datetime(input_str: str) -> Optional[datetime]:
    """Parse datetime string from user input."""
    if not input_str or input_str.strip().lower() in ["none", ""]:
        return None
    
    try:
        formats = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d-%H%M",
            "%Y-%m-%d",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(input_str.strip(), fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Invalid date format: {input_str}")
    
    except Exception as e:
        console.print(f"[red]Error parsing date:[/red] {e}")
        return None


def get_user_inputs() -> Tuple[List[str], Optional[datetime], Optional[datetime]]:
    """Collect pipeline parameters from user interactively."""
    console.print("\n[bold cyan]Pipeline Configuration[/bold cyan]\n")
    
    # Get symbols
    console.print("[dim]Examples: BINANCE:BTCUSDT.P, BINANCE:ETHUSDT.P[/dim]")
    symbols_input = Prompt.ask(
        "Enter symbols (comma-separated)",
        default="BINANCE:BTCUSDT.P, BINANCE:ETHUSDT.P",
    )
    symbols = parse_symbols(symbols_input)
    
    # Get start date
    console.print("\n[dim]Format: YYYY-MM-DD HH:MM (e.g., 2025-11-01 07:00)[/dim]")
    console.print("[dim]Press Enter to skip[/dim]")
    start_input = Prompt.ask(
        "Start date",
        default="",
        show_default=False,
    )
    start_date = parse_datetime(start_input)
    
    # Get end date
    console.print("\n[dim]Format: YYYY-MM-DD HH:MM (e.g., 2025-12-01 07:00)[/dim]")
    console.print("[dim]Press Enter to skip[/dim]")
    end_input = Prompt.ask(
        "End date",
        default="",
        show_default=False,
    )
    end_date = parse_datetime(end_input)
    
    # Show summary
    console.print("\n[bold yellow]Configuration Summary:[/bold yellow]")
    console.print(f"  Symbols: {', '.join(symbols)}")
    console.print(f"  Start: {start_date.isoformat() if start_date else 'Default'}")
    console.print(f"  End: {end_date.isoformat() if end_date else 'Default'}")
    console.print()
    
    return symbols, start_date, end_date


def display_stage_data_detailed(stage_name: str, pipeline_data: Dict[str, Any]) -> None:
    """Display detailed data for a specific stage."""
    config = STAGE_CONFIG.get(stage_name)
    if not config:
        return
    
    name = config["name"]
    
    console.print(f"\n[bold cyan]{name} - Detailed Results[/bold cyan]")
    console.print("─" * 80)
    
    # Health Check
    if stage_name == "health_check":
        health = pipeline_data.get("health_check", {})
        status = health.get("overall_status", "unknown")
        
        # Status panel
        status_color = "green" if status == "healthy" else "yellow" if status == "degraded" else "red"
        console.print(Panel(
            f"[bold {status_color}]{status.upper()}[/bold {status_color}]\n"
            f"APIs Healthy: {health.get('apis_healthy', 0)}/{health.get('apis_checked', 0)}",
            title="System Health",
            border_style=status_color,
        ))
        
        # API details table
        if health.get("api_details"):
            table = Table(title="API Status Details", show_header=True)
            table.add_column("API Type", style="cyan")
            table.add_column("Status", style="white")
            
            for api in health.get("api_details", []):
                api_type = api.get("type", "unknown")
                api_status = api.get("status", "unknown")
                status_icon = "✓" if api_status == "healthy" else "✗"
                status_color = "green" if api_status == "healthy" else "red"
                table.add_row(
                    api_type.upper(),
                    f"[{status_color}]{status_icon} {api_status}[/{status_color}]"
                )
            
            console.print(table)
    
    # Data Collection
    elif stage_name == "data_collection":
        raw_data = pipeline_data.get("raw_data", [])
        summary = pipeline_data.get("collection_summary", {})
        
        # Summary metrics
        metrics_table = Table(title="Collection Metrics", show_header=True)
        metrics_table.add_column("Metric", style="cyan", width=30)
        metrics_table.add_column("Value", style="yellow", justify="right")
        
        metrics_table.add_row("Total Records Collected", f"{summary.get('total_records', 0):,}")
        metrics_table.add_row("Successful Fetches", f"{summary.get('successful', 0)}")
        metrics_table.add_row("Failed Fetches", f"{summary.get('failed', 0)}")
        
        console.print(metrics_table)
        
        # Data breakdown by type and symbol
        if raw_data:
            type_symbol_counts = {}
            for record in raw_data:
                schema_type = record.get("schema_type", "unknown")
                symbol = record.get("symbol", "unknown")
                key = f"{schema_type}:{symbol}"
                type_symbol_counts[key] = type_symbol_counts.get(key, 0) + 1
            
            breakdown_table = Table(title="Data Breakdown", show_header=True)
            breakdown_table.add_column("Data Type", style="cyan")
            breakdown_table.add_column("Symbol", style="magenta")
            breakdown_table.add_column("Records", style="yellow", justify="right")
            
            for key, count in sorted(type_symbol_counts.items()):
                data_type, symbol = key.split(":", 1)
                breakdown_table.add_row(data_type, symbol, f"{count:,}")
            
            console.print(breakdown_table)
            
            # Sample data preview
            if len(raw_data) > 0:
                console.print("\n[bold]Sample Record (First Entry):[/bold]")
                sample = raw_data[0]
                sample_json = json.dumps({
                    "symbol": sample.get("symbol"),
                    "schema_type": sample.get("schema_type"),
                    "vendor": sample.get("vendor"),
                    "data_sample": str(sample.get("data", {}))[:200] + "..."
                }, indent=2)
                syntax = Syntax(sample_json, "json", theme="monokai", line_numbers=True)
                console.print(syntax)
    
    # NaN Processing
    elif stage_name == "nan_processing":
        stats = pipeline_data.get("nan_stats", {})
        processed_data = pipeline_data.get("processed_data", [])
        
        console.print(Panel(
            f"NaN Values Cleaned: [yellow]{stats.get('nan_count', 0)}[/yellow]\n"
            f"Records Processed: [green]{len(processed_data):,}[/green]",
            title="Cleaning Summary",
            border_style="yellow",
        ))
    
    # Temporal Alignment
    elif stage_name == "temporal_alignment":
        stats = pipeline_data.get("alignment_stats", {})
        aligned_data = pipeline_data.get("aligned_data", [])
        
        table = Table(title="Alignment Results", show_header=True)
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", style="yellow", justify="right")
        
        table.add_row("Aligned Successfully", f"{stats.get('aligned_count', 0):,}")
        table.add_row("Alignment Failed", f"{stats.get('failed_count', 0):,}")
        table.add_row("Alignment Rate", f"{stats.get('alignment_rate', '0%')}")
        table.add_row("Total Records", f"{len(aligned_data):,}")
        
        console.print(table)
        
        # Show timestamp sample
        if aligned_data:
            console.print("\n[bold]Sample Timestamps (First 3 records):[/bold]")
            for i, record in enumerate(aligned_data[:3], 1):
                timestamp = record.get("data", {}).get("timestamp", "N/A")
                symbol = record.get("symbol", "unknown")
                console.print(f"  {i}. {symbol}: [cyan]{timestamp}[/cyan]")
    
    # Deduplication
    elif stage_name == "deduplication":
        stats = pipeline_data.get("dedup_stats", {})
        unique_data = pipeline_data.get("unique_data", [])
        
        # Main metrics
        table = Table(title="Deduplication Results", show_header=True)
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", style="yellow", justify="right")
        
        table.add_row("Duplicates Removed", f"[red]{stats.get('duplicates_removed', 0):,}[/red]")
        table.add_row("Unique Records", f"[green]{stats.get('unique_records', 0):,}[/green]")
        table.add_row("Duplicate Rate", f"{stats.get('duplicate_rate', '0%')}")
        
        console.print(table)
        
        # Breakdown by type
        if unique_data:
            type_counts = {}
            for record in unique_data:
                schema_type = record.get("schema_type", "unknown")
                type_counts[schema_type] = type_counts.get(schema_type, 0) + 1
            
            console.print("\n[bold]Unique Records by Type:[/bold]")
            for data_type, count in sorted(type_counts.items()):
                console.print(f"  • {data_type}: [cyan]{count:,}[/cyan]")
    
    # Quality Assurance
    elif stage_name == "quality_assurance":
        stats = pipeline_data.get("qa_stats", {})
        validated_data = pipeline_data.get("validated_data", [])
        
        threshold_met = stats.get("threshold_met", False)
        status_color = "green" if threshold_met else "yellow"
        
        # Main panel
        console.print(Panel(
            f"Records Passed: [{status_color}]{stats.get('qa_passed', 0):,}[/{status_color}]\n"
            f"Records Failed: [red]{stats.get('qa_failed', 0):,}[/red]\n"
            f"Pass Rate: [{status_color}]{stats.get('pass_rate', '0%')}[/{status_color}]\n"
            f"Threshold Met: [{status_color}]{'✓' if threshold_met else '✗'}[/{status_color}]",
            title="Quality Check Results",
            border_style=status_color,
        ))
        
        # Issues summary
        issues = stats.get("issues", [])
        if issues:
            console.print("\n[bold red]Quality Issues Found:[/bold red]")
            issue_table = Table(show_header=True)
            issue_table.add_column("Symbol", style="cyan")
            issue_table.add_column("Type", style="magenta")
            issue_table.add_column("Issues", style="red")
            
            for issue in issues[:10]:  # Show first 10
                issue_table.add_row(
                    issue.get("symbol", "N/A"),
                    issue.get("schema_type", "N/A"),
                    ", ".join(issue.get("issues", []))
                )
            
            console.print(issue_table)
    
    # Data Export
    elif stage_name == "data_export":
        stats = pipeline_data.get("export_stats", {})
        
        # Export summary
        table = Table(title="Export Summary", show_header=True)
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", style="yellow")
        
        table.add_row("Records Exported", f"{stats.get('records_exported', 0):,}")
        table.add_row("Files Created", f"{len(stats.get('exported_files', []))}")
        table.add_row("Output Directory", stats.get('output_directory', 'N/A'))
        
        console.print(table)
        
        # File tree
        exported_files = stats.get("exported_files", [])
        if exported_files:
            console.print("\n[bold]Exported Files:[/bold]")
            tree = Tree("Output")
            for file_path in exported_files[:10]:  # Show first 10
                tree.add(f"{file_path}")
            console.print(tree)
    
    console.print()


async def run_pipeline_with_detailed_tracking(
    farm: ResilientDataFarm,
    symbols: List[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    show_details: bool = True
):
    """Run pipeline with detailed data tracking and display."""
    
    # Create progress display
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    )
    
    stage_results = []
    
    with Live(progress, console=console, refresh_per_second=10):
        # Create main progress task
        main_task = progress.add_task(
            "[cyan]Pipeline Progress",
            total=7
        )
        
        # Initialize pipeline data
        pipeline_start = datetime.utcnow()
        pipeline_data = {
            "pipeline_start": pipeline_start.isoformat(),
            "adapters": farm.get_adapters(),
            "symbols": symbols,
            "config": farm.get_config(),
            "start_date": start_date,
            "end_date": end_date,
        }
        
        # Execute each stage
        for idx, stage in enumerate(farm.stages, 1):
            stage_name = stage.stage_name
            config = STAGE_CONFIG.get(stage_name, {})
            display_name = config.get("name", stage_name.replace("_", " ").title())
            
            # Update progress
            progress.update(
                main_task,
                description=f"[cyan]Stage {idx}/7: {display_name}...",
            )
            
            # Execute stage
            stage_start = datetime.utcnow()
            try:
                pipeline_data = await stage.execute(pipeline_data)
                stage_end = datetime.utcnow()
                duration = (stage_end - stage_start).total_seconds()
                
                # Store result
                stage_results.append({
                    "stage": display_name,
                    "stage_name": stage_name,
                    "status": "✓",
                    "duration": f"{duration:.2f}s",
                    "success": True,
                })
                
                # Update progress
                progress.update(main_task, advance=1)
                
                # Check for critical failures
                if stage_name == "health_check":
                    health = pipeline_data.get("health_check", {})
                    if health.get("overall_status") == "critical":
                        raise RuntimeError("Health check failed: APIs unavailable")
                
                elif stage_name == "data_collection":
                    summary = pipeline_data.get("collection_summary", {})
                    if summary.get("successful", 0) == 0:
                        raise RuntimeError("Data collection failed: No data fetched")
                
            except Exception as e:
                stage_end = datetime.utcnow()
                duration = (stage_end - stage_start).total_seconds()
                
                stage_results.append({
                    "stage": display_name,
                    "stage_name": stage_name,
                    "status": "✗",
                    "duration": f"{duration:.2f}s",
                    "success": False,
                    "error": str(e),
                })
                
                progress.update(main_task, description="[red]Pipeline Failed")
                raise
        
        # Complete
        progress.update(main_task, description="[green]Pipeline Complete!")
    
    # Show detailed results for each stage
    if show_details:
        console.print("\n\n")
        console.print("=" * 80)
        console.print("[bold cyan]DETAILED STAGE RESULTS[/bold cyan]")
        console.print("=" * 80)
        
        for result in stage_results:
            if result["success"]:
                display_stage_data_detailed(result["stage_name"], pipeline_data)
    
    # Calculate total duration
    pipeline_end = datetime.utcnow()
    total_duration = (pipeline_end - pipeline_start).total_seconds()
    
    return stage_results, pipeline_data, total_duration


def display_final_summary(stage_results: list, pipeline_data: dict, total_duration: float):
    """Display comprehensive final summary."""
    
    console.print("\n\n")
    console.print("=" * 80)
    console.print("[bold cyan]PIPELINE EXECUTION SUMMARY[/bold cyan]")
    console.print("=" * 80)
    console.print()
    
    # Stage execution table
    table = Table(title="Stage Execution Timeline", show_header=True, expand=True)
    table.add_column("Stage", style="cyan", width=30)
    table.add_column("Status", style="white", width=10, justify="center")
    table.add_column("Duration", style="yellow", width=12, justify="right")
    
    for result in stage_results:
        status_display = f"[green]{result['status']}[/green]" if result['success'] else f"[red]{result['status']}[/red]"
        table.add_row(
            result['stage'],
            status_display,
            result['duration']
        )
    
    console.print(table)
    console.print()
    
    # Key metrics panel
    export_stats = pipeline_data.get("export_stats", {})
    collection_summary = pipeline_data.get("collection_summary", {})
    qa_stats = pipeline_data.get("qa_stats", {})
    
    metrics_panel = f"""[bold yellow]Total Duration:[/bold yellow] {total_duration:.2f}s
[bold yellow]Records Collected:[/bold yellow] {collection_summary.get('total_records', 0):,}
[bold yellow]Records Exported:[/bold yellow] {export_stats.get('records_exported', 0):,}
[bold yellow]Files Created:[/bold yellow] {len(export_stats.get('exported_files', []))}
[bold yellow]Quality Pass Rate:[/bold yellow] {qa_stats.get('pass_rate', 'N/A')}
[bold yellow]Output Directory:[/bold yellow] {export_stats.get('output_directory', 'N/A')}"""
    
    console.print(Panel(metrics_panel, title="Key Metrics", border_style="green"))
    console.print()
    console.print("=" * 80)
    console.print()


async def run_pipeline_async():
    """Execute pipeline with rich data visualization."""
    try:
        # Get user inputs
        symbols, start_date, end_date = get_user_inputs()
        
        # Ask if user wants detailed output
        show_details = Confirm.ask(
            "\n[bold yellow]Show detailed data for each stage?[/bold yellow]",
            default=True
        )
        
        # Confirm execution
        if not Confirm.ask("\n[bold yellow]Start pipeline execution?[/bold yellow]"):
            console.print("[yellow]Pipeline cancelled by user[/yellow]\n")
            return
        
        # Initialize Data Farm
        console.print("\n[cyan]Initializing ResilientDataFarm...[/cyan]")
        farm = ResilientDataFarm()
        console.print(f"[green]OK[/green] Loaded {len(farm.get_adapters())} adapters")
        console.print(f"[green]OK[/green] Initialized {len(farm.stages)} stages\n")
        
        # Run pipeline
        stage_results, pipeline_data, total_duration = await run_pipeline_with_detailed_tracking(
            farm, symbols, start_date, end_date, show_details
        )
        
        # Display final summary
        display_final_summary(stage_results, pipeline_data, total_duration)
        
        console.print("[bold green]Pipeline completed successfully![/bold green]\n")
        
    except KeyboardInterrupt:
        console.print("\n[bold red]Pipeline interrupted by user[/bold red]\n")
    except Exception as e:
        console.print(f"\n[bold red]Pipeline failed: {e}[/bold red]\n")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


def main():
    """Main entry point for enhanced run_pipeline command."""
    console.print(
        Padding(
            Panel.fit(
                "[bold cyan]Marketpilot Data Farm Pipeline[/bold cyan]\n"
                "Enhanced data collection with detailed stage insights",
                border_style="magenta",
            ),
            (1, 0, 1, 0),
        )
    )
    
    asyncio.run(run_pipeline_async())


if __name__ == "__main__":
    main()