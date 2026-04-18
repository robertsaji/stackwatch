"""CLI commands for escalation policy inspection."""
import click
from stackwatch.severity import SeverityLevel
from stackwatch.escalation import EscalationConfig, EscalationRule


@click.group(name="escalation")
def escalation_group():
    """Manage escalation rules."""


@escalation_group.command("list")
@click.option("--config-file", default=None, help="Path to escalation config JSON.")
def list_rules(config_file):
    """List all escalation rules."""
    import json, pathlib
    if config_file and pathlib.Path(config_file).exists():
        data = json.loads(pathlib.Path(config_file).read_text())
        rules = [
            EscalationRule(
                min_level=SeverityLevel[r["min_level"]],
                notifier_name=r["notifier_name"],
            )
            for r in data.get("rules", [])
        ]
    else:
        rules = []
    if not rules:
        click.echo("No escalation rules configured.")
        return
    for rule in rules:
        click.echo(f"  [{rule.min_level.name}] -> {rule.notifier_name}")


@escalation_group.command("check")
@click.argument("stack_name")
@click.argument("drifted_count", type=int)
def check_level(stack_name, drifted_count):
    """Show escalation level for a given drift count."""
    from stackwatch.severity import SeverityLevel
    if drifted_count == 0:
        level = SeverityLevel.LOW
    elif drifted_count <= 2:
        level = SeverityLevel.MEDIUM
    elif drifted_count <= 5:
        level = SeverityLevel.HIGH
    else:
        level = SeverityLevel.CRITICAL
    click.echo(f"Stack '{stack_name}' with {drifted_count} drifted resource(s): {level.name}")
