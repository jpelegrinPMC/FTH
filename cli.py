import os
import json
import sys
import asyncio
import click
from typing import Optional, Any

# Import FutureHouseClient and JobNames from the official package
# See documentation lines 80-110 for examples of use
# 【F:INFOGUIDE.txt†L80-L110】
try:
    from futurehouse_client import FutureHouseClient, JobNames
except ImportError:  # library might not be installed in this environment
    FutureHouseClient = None
    JobNames = None


def get_api_key(api_key_option: Optional[str]) -> str:
    """Get API key from option or environment variable."""
    api_key = api_key_option or os.getenv("FUTUREHOUSE_API_KEY")
    if not api_key:
        raise click.BadParameter(
            "API key not provided. Use --api-key option or set FUTUREHOUSE_API_KEY environment variable"
        )
    return api_key


def create_client(api_key: str) -> "FutureHouseClient":
    """Create a FutureHouseClient instance."""
    if FutureHouseClient is None:
        raise RuntimeError(
            "futurehouse-client package is not installed. Install it via pip install futurehouse-client"
        )
    return FutureHouseClient(api_key=api_key)


def object_to_jsonable(obj: Any) -> Any:
    """Convert pydantic or dataclass objects into JSON-serializable dicts."""
    if isinstance(obj, list):
        return [object_to_jsonable(i) for i in obj]
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return obj


def handle_http_error(error: Exception):
    """Handle HTTP and API errors with user-friendly messages."""
    message = str(error)
    status = getattr(error, "status_code", None)
    if status is None and hasattr(error, "response") and error.response is not None:
        status = getattr(error.response, "status_code", None)
    if status in {400, 401, 403, 429, 500, 503}:
        click.echo(f"Error {status}: {message}", err=True)
    else:
        click.echo(f"Error: {message}", err=True)


@click.group()
@click.option("--api-key", help="API key for FutureHouse", envvar="FUTUREHOUSE_API_KEY")
@click.pass_context
def cli(ctx, api_key):
    """FutureHouse command line interface."""
    ctx.obj = {"api_key": api_key}


@cli.command()
@click.option("--name", required=True, type=str, help="Agent name (e.g. CROW, OWL)")
@click.option("--query", required=True, help="Query text for the task")
@click.option("--task-id", "task_id", help="Optional task UUID")
@click.option("--continued-task-id", help="ID of previous task for follow-up")
@click.option("--timeout", type=int, help="Execution timeout in seconds")
@click.option("--max-steps", type=int, help="Maximum steps to run")
@click.pass_context
def create(ctx, name, query, task_id, continued_task_id, timeout, max_steps):
    """Create a task and return its ID."""
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    runtime_config = {}
    if continued_task_id:
        runtime_config["continued_task_id"] = continued_task_id
    if timeout:
        runtime_config["timeout"] = timeout
    if max_steps:
        runtime_config["max_steps"] = max_steps

    task_data = {
        "name": getattr(JobNames, name, name),
        "query": query,
        "id": task_id,
        "runtime_config": runtime_config or None,
    }
    try:
        task_id_resp = client.create_task(task_data)
        click.echo(task_id_resp)
    except Exception as e:  # handle HTTP errors gracefully
        handle_http_error(e)


@cli.command()
@click.option("--name", required=True, type=str, help="Agent name (e.g. CROW, OWL)")
@click.option("--query", required=True, help="Query text for the task")
@click.option("--task-id", "task_id", help="Optional task UUID")
@click.option("--continued-task-id", help="ID of previous task for follow-up")
@click.option("--timeout", type=int, help="Execution timeout in seconds")
@click.option("--max-steps", type=int, help="Maximum steps to run")
@click.option("--verbose", is_flag=True, help="Return detailed response")
@click.pass_context
def run(ctx, name, query, task_id, continued_task_id, timeout, max_steps, verbose):
    """Create and run a task until completion."""
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    runtime_config = {}
    if continued_task_id:
        runtime_config["continued_task_id"] = continued_task_id
    if timeout:
        runtime_config["timeout"] = timeout
    if max_steps:
        runtime_config["max_steps"] = max_steps

    task_data = {
        "name": getattr(JobNames, name, name),
        "query": query,
        "id": task_id,
        "runtime_config": runtime_config or None,
    }
    try:
        response = client.run_tasks_until_done(task_data, verbose=verbose)
        click.echo(json.dumps(object_to_jsonable(response), ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


@cli.command()
@click.option("--name", required=True, type=str, help="Agent name (e.g. CROW, OWL)")
@click.option("--query", required=True, help="Query text for the task")
@click.option("--task-id", "task_id", help="Optional task UUID")
@click.option("--continued-task-id", help="ID of previous task for follow-up")
@click.option("--timeout", type=int, help="Execution timeout in seconds")
@click.option("--max-steps", type=int, help="Maximum steps to run")
@click.option("--verbose", is_flag=True, help="Return detailed response")
@click.pass_context
def arun(ctx, name, query, task_id, continued_task_id, timeout, max_steps, verbose):
    """Asynchronously create and run a task until completion."""
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    runtime_config = {}
    if continued_task_id:
        runtime_config["continued_task_id"] = continued_task_id
    if timeout:
        runtime_config["timeout"] = timeout
    if max_steps:
        runtime_config["max_steps"] = max_steps

    task_data = {
        "name": getattr(JobNames, name, name),
        "query": query,
        "id": task_id,
        "runtime_config": runtime_config or None,
    }
    try:
        response = asyncio.run(client.arun_tasks_until_done(task_data, verbose=verbose))
        click.echo(json.dumps(object_to_jsonable(response), ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


@cli.command(name="batch")
@click.option("--file", "file_", required=True, type=click.Path(exists=True), help="JSON file with an array of tasks")
@click.option("--verbose", is_flag=True, help="Return detailed responses")
@click.pass_context
def run_batch(ctx, file_, verbose):
    """Run multiple tasks from a JSON file."""
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    with open(file_, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    try:
        responses = client.run_tasks_until_done(tasks, verbose=verbose)
        click.echo(json.dumps(object_to_jsonable(responses), ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


@cli.command(name="abatch")
@click.option("--file", "file_", required=True, type=click.Path(exists=True), help="JSON file with an array of tasks")
@click.option("--verbose", is_flag=True, help="Return detailed responses")
@click.pass_context
def run_abatch(ctx, file_, verbose):
    """Run multiple tasks asynchronously from a JSON file."""
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    with open(file_, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    try:
        responses = asyncio.run(client.arun_tasks_until_done(tasks, verbose=verbose))
        click.echo(json.dumps(object_to_jsonable(responses), ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


@cli.command()
@click.argument("task_id")
@click.pass_context
def status(ctx, task_id):
    """Get the current status of a task."""
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    try:
        status_resp = client.get_task_status(task_id)
        click.echo(json.dumps(object_to_jsonable(status_resp), ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


@cli.command()
@click.argument("task_id")
@click.pass_context
def result(ctx, task_id):
    """Get the final result for a completed task."""
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    try:
        try:
            res = client.get_task_result(task_id)
        except AttributeError:
            # Fallback for older client versions
            res = getattr(client, "get_task", lambda _id: None)(task_id)
        click.echo(json.dumps(object_to_jsonable(res), ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


if __name__ == "__main__":
    cli()
