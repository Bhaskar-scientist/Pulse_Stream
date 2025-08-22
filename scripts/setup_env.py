#!/usr/bin/env python3
"""Environment setup script for PulseStream."""

import os
import secrets
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()
app = typer.Typer()


def generate_secret_key() -> str:
    """Generate a secure secret key."""
    return secrets.token_urlsafe(32)


@app.command()
def setup(
    environment: str = typer.Option(
        "development", 
        help="Environment to setup (development/production/test)"
    ),
    force: bool = typer.Option(
        False, 
        "--force", 
        help="Overwrite existing .env file"
    )
):
    """Setup environment configuration for PulseStream."""
    
    console.print(Panel.fit(
        f"🚀 [bold blue]PulseStream Environment Setup[/bold blue]\n"
        f"Setting up: [yellow]{environment}[/yellow]",
        border_style="blue"
    ))
    
    env_file = Path(".env")
    
    # Check if .env already exists
    if env_file.exists() and not force:
        if not Confirm.ask(f".env file already exists. Overwrite?"):
            console.print("❌ Setup cancelled")
            return
    
    # Choose template based on environment
    if environment == "production":
        template_file = Path(".env.production")
    elif environment == "test":
        template_file = Path(".env.test")
    else:
        template_file = Path("env-example")
    
    if not template_file.exists():
        console.print(f"❌ Template file {template_file} not found")
        return
    
    # Copy template to .env
    shutil.copy(template_file, env_file)
    console.print(f"✅ Copied {template_file} to .env")
    
    # Generate and replace secret key
    secret_key = generate_secret_key()
    content = env_file.read_text()
    
    if environment == "development":
        # For development, use a fixed but secure key
        content = content.replace(
            "your-secret-key-here-must-be-complex",
            f"dev-{secret_key}"
        )
    else:
        # For production/test, replace placeholder
        content = content.replace(
            "CHANGE-THIS-TO-A-STRONG-SECRET-KEY",
            secret_key
        ).replace(
            "test-secret-key-not-for-production",
            f"test-{secret_key}"
        )
    
    env_file.write_text(content)
    console.print(f"✅ Generated secure SECRET_KEY")
    
    # Show next steps
    console.print("\n📋 [bold green]Next Steps:[/bold green]")
    console.print("1. Review and update .env file with your actual values")
    console.print("2. Update database credentials if needed")
    console.print("3. Configure email/Slack settings for alerts")
    
    if environment == "development":
        console.print("4. Run: [cyan]docker-compose up -d[/cyan] to start services")
        console.print("5. Run: [cyan]poetry run uvicorn main:app --reload[/cyan] to start the app")
    
    console.print(f"\n🎉 Environment setup complete for: [green]{environment}[/green]")


@app.command()
def validate():
    """Validate current environment configuration."""
    
    console.print("🔍 [bold blue]Validating Environment Configuration[/bold blue]")
    
    env_file = Path(".env")
    if not env_file.exists():
        console.print("❌ .env file not found. Run: [cyan]python scripts/setup_env.py setup[/cyan]")
        return
    
    # Read environment variables
    env_vars = {}
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    
    # Required variables
    required_vars = [
        "ENVIRONMENT",
        "SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND"
    ]
    
    missing_vars = []
    weak_vars = []
    
    for var in required_vars:
        if var not in env_vars or not env_vars[var]:
            missing_vars.append(var)
        elif var == "SECRET_KEY" and len(env_vars[var]) < 32:
            weak_vars.append(var)
    
    # Show validation results
    if missing_vars:
        console.print(f"❌ Missing required variables: {', '.join(missing_vars)}")
    
    if weak_vars:
        console.print(f"⚠️  Weak configuration: {', '.join(weak_vars)}")
    
    if not missing_vars and not weak_vars:
        console.print("✅ All required environment variables are configured")
        
        # Show current environment
        environment = env_vars.get("ENVIRONMENT", "unknown")
        console.print(f"📍 Current environment: [green]{environment}[/green]")
    
    return len(missing_vars) == 0 and len(weak_vars) == 0


@app.command()
def show():
    """Show current environment configuration (without secrets)."""
    
    env_file = Path(".env")
    if not env_file.exists():
        console.print("❌ .env file not found")
        return
    
    console.print("📋 [bold blue]Current Environment Configuration[/bold blue]")
    
    for line in env_file.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            if "=" in line:
                key, value = line.split("=", 1)
                # Hide sensitive values
                if any(sensitive in key.upper() for sensitive in ["SECRET", "PASSWORD", "KEY", "TOKEN"]):
                    value = "***HIDDEN***"
                console.print(f"[cyan]{key}[/cyan] = [yellow]{value}[/yellow]")


if __name__ == "__main__":
    app()
