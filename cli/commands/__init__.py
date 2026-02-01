"""
CLI command modules.
"""

# Import all command modules to register them
import cli.commands.analyze
import cli.commands.budget
import cli.commands.alerts
import cli.commands.credentials
import cli.commands.config
import cli.commands.optimize

__all__ = [
    "analyze",
    "budget",
    "alerts", 
    "credentials",
    "config",
    "optimize",
]
