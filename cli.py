import os
import json
import sys
import asyncio
import click
from typing import Optional

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


def handle_http_error(error: Exception):
    """Handle HTTP and API errors with user-friendly messages.

    Error codes documented in the guide: 400, 401, 403, 429, 500, 503.
    See 【F:INFOGUIDE.txt†L288-L299】
    """
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
@click.option("--runtime-config", "runtime_config_json", help="Additional runtime configuration as JSON")
@click.pass_context
def create(ctx, name, query, task_id, continued_task_id, timeout, max_steps, runtime_config_json):
    """Create a task and return its ID."""
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    runtime_config = {}
    if runtime_config_json:
        try:
            runtime_config.update(json.loads(runtime_config_json))
        except json.JSONDecodeError as exc:
            raise click.BadParameter(f"Invalid JSON for runtime-config: {exc}") from exc
    if continued_task_id:
        # Follow-up task example 【F:INFOGUIDE.txt†L148-L165】
        runtime_config["continued_task_id"] = continued_task_id
    if timeout:
        runtime_config["timeout"] = timeout
    if max_steps:
        runtime_config["max_steps"] = max_steps

    job_name = (
        JobNames.from_string(name)
        if JobNames and hasattr(JobNames, "from_string")
        else getattr(JobNames, name, name)
    )
    task_data = {
        "name": job_name,
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
@click.option("--runtime-config", "runtime_config_json", help="Additional runtime configuration as JSON")
@click.option("--verbose", is_flag=True, help="Return detailed response")
@click.pass_context
def run(ctx, name, query, task_id, continued_task_id, timeout, max_steps, runtime_config_json, verbose):
    """Create and run a task until completion."""
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    runtime_config = {}
    if runtime_config_json:
        try:
            runtime_config.update(json.loads(runtime_config_json))
        except json.JSONDecodeError as exc:
            raise click.BadParameter(f"Invalid JSON for runtime-config: {exc}") from exc
    if continued_task_id:
        # Follow-up task example 【F:INFOGUIDE.txt†L148-L165】
        runtime_config["continued_task_id"] = continued_task_id
    if timeout:
        runtime_config["timeout"] = timeout
    if max_steps:
        runtime_config["max_steps"] = max_steps

    job_name = (
        JobNames.from_string(name)
        if JobNames and hasattr(JobNames, "from_string")
        else getattr(JobNames, name, name)
    )
    task_data = {
        "name": job_name,
        "query": query,
        "id": task_id,
        "runtime_config": runtime_config or None,
    }
    try:
        response = client.run_tasks_until_done(task_data, verbose=verbose)
        click.echo(json.dumps(response, ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


@cli.command(name="arun")
@click.option("--name", required=True, type=str, help="Agent name (e.g. CROW, OWL)")
@click.option("--query", required=True, help="Query text for the task")
@click.option("--task-id", "task_id", help="Optional task UUID")
@click.option("--continued-task-id", help="ID of previous task for follow-up")
@click.option("--timeout", type=int, help="Execution timeout in seconds")
@click.option("--max-steps", type=int, help="Maximum steps to run")
@click.option("--runtime-config", "runtime_config_json", help="Additional runtime configuration as JSON")
@click.option("--verbose", is_flag=True, help="Return detailed response")
@click.pass_context
def async_run(ctx, name, query, task_id, continued_task_id, timeout, max_steps, runtime_config_json, verbose):
    """Run a task asynchronously until completion."""
    # See asynchronous example in docs 【F:INFOGUIDE.txt†L92-L118】
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)

    runtime_config = {}
    if runtime_config_json:
        try:
            runtime_config.update(json.loads(runtime_config_json))
        except json.JSONDecodeError as exc:
            raise click.BadParameter(f"Invalid JSON for runtime-config: {exc}") from exc
    if continued_task_id:
        # Follow-up task example 【F:INFOGUIDE.txt†L148-L165】
        runtime_config["continued_task_id"] = continued_task_id
    if timeout:
        runtime_config["timeout"] = timeout
    if max_steps:
        runtime_config["max_steps"] = max_steps

    job_name = (
        JobNames.from_string(name)
        if JobNames and hasattr(JobNames, "from_string")
        else getattr(JobNames, name, name)
    )
    task_data = {
        "name": job_name,
        "query": query,
        "id": task_id,
        "runtime_config": runtime_config or None,
    }

    async def _run():
        return await client.arun_tasks_until_done(task_data, verbose=verbose)

    try:
        response = asyncio.run(_run())
        click.echo(json.dumps(response, ensure_ascii=False, indent=2))
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
        click.echo(json.dumps(responses, ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


@cli.command(name="abatch")
@click.option("--file", "file_", required=True, type=click.Path(exists=True), help="JSON file with an array of tasks")
@click.option("--verbose", is_flag=True, help="Return detailed responses")
@click.pass_context
def async_batch(ctx, file_, verbose):
    """Run multiple tasks asynchronously from a JSON file.

    Based on async batch example 【F:INFOGUIDE.txt†L120-L140】
    """
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    with open(file_, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    async def _run():
        return await client.arun_tasks_until_done(tasks, verbose=verbose)

    try:
        responses = asyncio.run(_run())
        click.echo(json.dumps(responses, ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


@cli.command()
@click.argument("task_id")
@click.pass_context
def status(ctx, task_id):
    """Get the current status of a task.

    Polling example in docs 【F:INFOGUIDE.txt†L338-L349】
    """
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    try:
        status_resp = client.get_task_status(task_id)
        click.echo(json.dumps(status_resp, ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


@cli.command()
@click.argument("task_id")
@click.pass_context
def result(ctx, task_id):
    """Get the final result for a completed task.

    See polling example in docs 【F:INFOGUIDE.txt†L338-L349】
    """
    api_key = get_api_key(ctx.obj.get("api_key"))
    client = create_client(api_key)
    try:
        res = client.get_task_result(task_id)
        click.echo(json.dumps(res, ensure_ascii=False, indent=2))
    except Exception as e:
        handle_http_error(e)


if __name__ == "__main__":
    cli()