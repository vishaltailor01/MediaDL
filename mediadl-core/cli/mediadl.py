#!/usr/bin/env python3
import argparse
import sys
import os
import json
import requests
import glob

API_BASE_URL = os.getenv("MEDIADL_API_URL", "http://localhost:8000")

def local_engine():
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from engine.ffmpeg_wrapper import FfmpegEngine
    return FfmpegEngine()

def run_local_job(type_, input_path, format_, output_path=None, start=None, duration=None, dry_run=False):
    if not output_path:
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}.{format_}"
    
    if dry_run:
        print(f"[DRY-RUN] Local {type_} on {input_path} -> {output_path}")
        return output_path
        
    engine = local_engine()
    if type_ == "convert" or type_ == "extract":
        return engine.convert(input_path, output_path, format_)
    elif type_ == "trim":
        return engine.trim(input_path, output_path, start, duration)
    return None

def run_remote_job(type_, input_path, format_, start=None, duration=None, dry_run=False):
    if dry_run:
        print(f"[DRY-RUN] Remote API {type_} {input_path}")
        return
        
    payload = {
        "type": "convert" if type_ == "extract" else type_,
        "input": input_path,
        "outputFormat": format_
    }
    if type_ == "trim":
        payload["trimStart"] = start
        payload["trimDuration"] = duration

    response = requests.post(f"{API_BASE_URL}/jobs", json=payload)
    response.raise_for_status()
    job = response.json()
    print(f"[{job['jobId']}] Job queued.")
    return job['jobId']

def handle_job_cmd(args):
    type_ = args.command
    out_format = args.format if hasattr(args, "format") else "mp4"
    
    if args.remote:
        run_remote_job(type_, args.input, out_format, getattr(args, 'start', None), getattr(args, 'duration', None), args.dry_run)
    else:
        try:
            res = run_local_job(type_, args.input, out_format, args.output, getattr(args, 'start', None), getattr(args, 'duration', None), args.dry_run)
            print(f"Success! Saved to {res}")
        except Exception as e:
            print(f"Failed: {e}", file=sys.stderr)
            sys.exit(1)

def handle_batch(args):
    files = glob.glob(os.path.join(args.directory, f"*.{args.ext}"))
    print(f"Found {len(files)} files to {args.operation}.")
    
    for f in files:
        if args.remote:
            run_remote_job(args.operation, f, args.format, dry_run=args.dry_run)
        else:
            try:
                res = run_local_job(args.operation, f, args.format, dry_run=args.dry_run)
                print(f"Processed: {res}")
            except Exception as e:
                print(f"Failed {f}: {e}")

def handle_status(args):
    try:
        response = requests.get(f"{API_BASE_URL}/jobs/{args.job_id}")
        response.raise_for_status()
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch job status: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="MediaDL Core CLI")
    parser.add_argument("--dry-run", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Convert
    p_conv = subparsers.add_parser("convert")
    p_conv.add_argument("input")
    p_conv.add_argument("--to", dest="format", required=True)
    p_conv.add_argument("-o", "--output")
    p_conv.add_argument("--remote", action="store_true")

    # Trim
    p_trim = subparsers.add_parser("trim")
    p_trim.add_argument("input")
    p_trim.add_argument("--start", help="00:00:10")
    p_trim.add_argument("--duration", help="00:00:05")
    p_trim.add_argument("--to", dest="format", default="mp4")
    p_trim.add_argument("-o", "--output")
    p_trim.add_argument("--remote", action="store_true")
    
    # Extract
    p_ext = subparsers.add_parser("extract")
    p_ext.add_argument("input")
    p_ext.add_argument("--to", dest="format", default="mp3")
    p_ext.add_argument("-o", "--output")
    p_ext.add_argument("--remote", action="store_true")

    # Batch
    p_batch = subparsers.add_parser("batch")
    p_batch.add_argument("operation", choices=["convert", "extract"])
    p_batch.add_argument("directory")
    p_batch.add_argument("--ext", default="mp4", help="Input extension")
    p_batch.add_argument("--to", dest="format", required=True)
    p_batch.add_argument("--remote", action="store_true")

    # Status
    p_status = subparsers.add_parser("status")
    p_status.add_argument("job_id")

    # Plugins
    p_plugin = subparsers.add_parser("plugin", help="Run a dynamically loaded processing plugin.")
    p_plugin.add_argument("name", help="Name of plugin to execute")
    p_plugin.add_argument("input")
    p_plugin.add_argument("-o", "--output", required=True)

    args = parser.parse_args()

    # Apply configuration defaults
    try:
        from config import load_config, resolve_cmd_args
        cfg = load_config()
        args = resolve_cmd_args(args, cfg)
    except:
        pass

    if args.command in ["convert", "trim", "extract"]:
        handle_job_cmd(args)
    elif args.command == "batch":
        handle_batch(args)
    elif args.command == "status":
        handle_status(args)
    elif args.command == "plugin":
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from engine.plugin_manager import PluginManager
        pm = PluginManager()
        try:
            res = pm.run_plugin(args.name, args.input, args.output)
            print(f"Plugin Executed! Saved to {res}")
        except Exception as e:
            print(f"Plugin error: {e}")

if __name__ == "__main__":
    main()
