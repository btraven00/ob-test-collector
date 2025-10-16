#!/usr/bin/env python3
"""
Dummy metric collector that demonstrates proper parameter handling.

This collector:
1. Uses glob patterns to find metrics.json files
2. Aggregates metrics (calculates avg, max, min, count)
3. Outputs aggregated results to metrics.json
4. Supports CLI parameters like the dummymodule
5. Outputs cli.txt for debugging
"""

import argparse
import json
import glob
import sys
from pathlib import Path
from typing import Dict, Any, List
import statistics


def parse_dynamic_args(argv):
    """Parse command line arguments with support for dynamic flags.

    Dynamic flags like --methods.result capture all arguments until the next flag.
    """
    # First pass: group arguments by flags
    grouped_args = {}
    current_flag = None
    i = 0

    while i < len(argv):
        arg = argv[i]

        if arg.startswith("--"):
            # New flag found
            current_flag = arg
            grouped_args[current_flag] = []
        elif current_flag:
            # Argument belongs to current flag
            grouped_args[current_flag].append(arg)
        else:
            # Positional argument (shouldn't happen with our usage)
            if "__positional__" not in grouped_args:
                grouped_args["__positional__"] = []
            grouped_args["__positional__"].append(arg)

        i += 1

    return grouped_args


def parse_args():
    """Parse command line arguments with support for dynamic flags."""
    # Get raw arguments (excluding script name)
    raw_args = sys.argv[1:]

    # Parse dynamic arguments
    dynamic_args = parse_dynamic_args(raw_args)

    # Create a namespace to hold all arguments
    args = argparse.Namespace()

    # Set defaults for known arguments
    args.input_pattern = "**/*_data.json"
    args.output_dir = None
    args.metric_key = "result"
    args.aggregation = "all"
    args.debug = False
    args.prefix = ""
    args.collector = None
    args.extra = []
    args.name = None

    # Store all dynamic arguments
    args.dynamic_args = {}

    # Process grouped arguments
    for flag, values in dynamic_args.items():
        flag_name = flag.lstrip("-").replace("-", "_")

        # Handle known flags
        if flag == "--input-pattern":
            args.input_pattern = values[0] if values else args.input_pattern
        elif flag == "--output_dir":
            args.output_dir = values[0] if values else None
        elif flag == "--metric-key":
            args.metric_key = values[0] if values else args.metric_key
        elif flag == "--aggregation":
            if values and values[0] in ["avg", "max", "min", "sum", "all"]:
                args.aggregation = values[0]
        elif flag == "--debug":
            args.debug = True  # Flag presence indicates True
        elif flag == "--prefix":
            args.prefix = values[0] if values else ""
        elif flag == "--collector":
            args.collector = values[0] if values else None
        elif flag == "--extra":
            args.extra.extend(values)
        elif flag == "--name":
            args.name = values[0] if values else None
        else:
            # Store unknown/dynamic arguments
            args.dynamic_args[flag] = values

    # Validate required arguments
    if not args.output_dir:
        raise SystemExit("Error: --output_dir is required")

    return args


def find_data_files(pattern: str, debug: bool = False) -> List[Path]:
    """Find all data files using glob pattern."""
    if debug:
        print(f"Searching for files with pattern: {pattern}")

    files = []
    for file_path in glob.glob(pattern, recursive=True):
        path_obj = Path(file_path)
        if path_obj.is_file():
            files.append(path_obj)
            if debug:
                print(f"Found data file: {file_path}")

    return files


def load_result_from_file(file_path: Path, metric_key: str, debug: bool = False) -> Any:
    """Load a specific result from a JSON file, return 'NA' if error field is not None."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        # Check if there's an error field
        if "error" in data and data["error"] is not None:
            if debug:
                print(f"Error found in {file_path}: {data['error']}, returning NA")
            return "NA"

        if metric_key in data:
            value = data[metric_key]
            if debug:
                print(f"Extracted {metric_key}={value} from {file_path}")
            return value
        else:
            if debug:
                print(
                    f"Key '{metric_key}' not found in {file_path}, available keys: {list(data.keys())}"
                )
            return "NA"

    except json.JSONDecodeError as e:
        if debug:
            print(f"JSON decode error in {file_path}: {e}")
        return "NA"
    except Exception as e:
        if debug:
            print(f"Error reading {file_path}: {e}")
        return "NA"


def aggregate_results(
    values: List[float], aggregation: str, debug: bool = False
) -> Dict[str, Any]:
    """Aggregate a list of numeric values."""
    if not values:
        return {"error": "No valid values found"}

    result = {}

    if aggregation == "all" or aggregation == "avg":
        result["avg"] = statistics.mean(values)

    if aggregation == "all" or aggregation == "max":
        result["max"] = max(values)

    if aggregation == "all" or aggregation == "min":
        result["min"] = min(values)

    if aggregation == "all" or aggregation == "sum":
        result["sum"] = sum(values)

    # Always include count and metadata
    result["count"] = len(values)
    result["values"] = values

    if debug:
        print(f"Aggregated {len(values)} values: {result}")

    return result


def save_cli_debug(args: argparse.Namespace, output_dir: Path):
    """Save CLI arguments to cli.txt for debugging (like dummymodule)."""
    cli_file = output_dir / "cli.txt"

    cli_content = [
        "=== DUMMY COLLECTOR CLI DEBUG ===",
        f"Script: {sys.argv[0]}",
        f"Arguments: {' '.join(sys.argv[1:])}",
        "",
        "=== PARSED ARGUMENTS ===",
    ]

    # Add known arguments
    for key, value in vars(args).items():
        if key != "dynamic_args":
            cli_content.append(f"{key}: {value}")

    # Add dynamic arguments
    if hasattr(args, "dynamic_args") and args.dynamic_args:
        cli_content.append("")
        cli_content.append("=== DYNAMIC ARGUMENTS ===")
        for flag, values in args.dynamic_args.items():
            cli_content.append(f"{flag}: {values}")

    cli_content.extend(
        [
            "",
            "=== ENVIRONMENT ===",
            f"Python: {sys.version}",
            f"Working directory: {Path.cwd()}",
            f"Output directory: {output_dir.absolute()}",
        ]
    )

    with open(cli_file, "w") as f:
        f.write("\n".join(cli_content))

    print(f"CLI debug info saved to: {cli_file}")


def main():
    """Main collector logic."""
    args = parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save CLI debug info (like dummymodule)
    save_cli_debug(args, output_dir)

    if args.debug:
        print("=== DUMMY COLLECTOR START ===")
        print(f"Input pattern: {args.input_pattern}")
        print(f"Output directory: {output_dir}")
        print(f"Metric key: {args.metric_key}")
        print(f"Aggregation: {args.aggregation}")

    # Find all data files using glob
    data_files = find_data_files(args.input_pattern, args.debug)

    if not data_files:
        error_result = {
            "error": f"No data files found with pattern: {args.input_pattern}",
            "pattern_used": args.input_pattern,
            "search_directory": str(Path.cwd().absolute()),
        }

        # Still save the error result
        output_file = output_dir / "metrics.json"
        with open(output_file, "w") as f:
            json.dump(error_result, f, indent=2)

        print(f"No data files found. Error result saved to: {output_file}")
        return 1

    # Extract result values from all files
    values = []
    file_info = []

    for file_path in data_files:
        value = load_result_from_file(file_path, args.metric_key, args.debug)
        if value != "NA":
            try:
                # Convert to float for aggregation
                numeric_value = float(value)
                values.append(numeric_value)
                file_info.append({"file": str(file_path), "value": numeric_value})
            except (ValueError, TypeError):
                if args.debug:
                    print(f"Skipping non-numeric value {value} from {file_path}")
                file_info.append(
                    {"file": str(file_path), "value": "NA", "error": "non-numeric"}
                )
        else:
            file_info.append({"file": str(file_path), "value": "NA"})

    # Perform aggregation
    aggregated = aggregate_results(values, args.aggregation, args.debug)

    # Add metadata
    result = {
        "aggregation_type": args.aggregation,
        "metric_key": args.metric_key,
        "input_pattern": args.input_pattern,
        "files_processed": len(file_info),
        "files_details": file_info,
        **aggregated,
    }

    # Add prefix if specified
    if args.prefix:
        prefixed_result = {}
        for key, value in result.items():
            if key not in [
                "files_details",
                "input_pattern",
                "metric_key",
                "aggregation_type",
            ]:
                prefixed_result[f"{args.prefix}_{key}"] = value
            else:
                prefixed_result[key] = value
        result = prefixed_result

    # Save aggregated metrics
    output_file = output_dir / "metrics.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Aggregated results from {len(file_info)} files saved to: {output_file}")

    if args.debug:
        print("=== AGGREGATION RESULT ===")
        print(json.dumps(result, indent=2))
        print("=== DUMMY COLLECTOR END ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
