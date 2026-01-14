"""
Credentials commands for secure credential management.
"""

import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint
import getpass

from ...core.config import Config
from ...core.exceptions import CloudBillingError, CredentialError
from ...core.credentials import CredentialManager

console = Console()

# Create credentials app
app = typer.Typer(
    name="credentials",
    help="Manage cloud credentials securely",
    no_args_is_help=True
)


@app.command()
def setup_aws(
    access_key_id: str = typer.Option(
        ...,
        "--access-key-id",
        help="AWS access key ID"
    ),
    secret_access_key: str = typer.Option(
        ...,
        "--secret-access-key",
        help="AWS secret access key"
    ),
    session_token: Optional[str] = typer.Option(
        None,
        "--session-token",
        help="AWS session token (optional)"
    )
) -> None:
    """Setup AWS credentials."""
    
    try:
        console.print("[blue]🔐 Setting up AWS credentials...[/blue]")
        
        # Initialize credential manager
        cred_mgr = CredentialManager()
        
        # Store credentials
        cred_mgr.setup_aws_credentials(access_key_id, secret_access_key, session_token)
        
        # Validate credentials
        if cred_mgr.validate_credentials("aws"):
            console.print(Panel.fit(
                "[bold green]✓ AWS credentials configured successfully[/bold green]\n\n"
                f"Access Key ID: {access_key_id[:8]}...{access_key_id[-4:]}\n"
                f"Session Token: {'Configured' if session_token else 'Not configured'}\n"
                f"Validation: ✓ Passed",
                title="AWS Credentials",
                border_style="green"
            ))
        else:
            console.print("[yellow]⚠ Credentials stored but validation failed[/yellow]")
            console.print("Please check your credentials and try again")
        
    except CredentialError as e:
        console.print(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def setup_azure(
    tenant_id: str = typer.Option(
        ...,
        "--tenant-id",
        help="Azure tenant ID"
    ),
    client_id: str = typer.Option(
        ...,
        "--client-id",
        help="Azure client ID"
    ),
    client_secret: str = typer.Option(
        ...,
        "--client-secret",
        help="Azure client secret"
    ),
    subscription_id: str = typer.Option(
        ...,
        "--subscription-id",
        help="Azure subscription ID"
    )
) -> None:
    """Setup Azure service principal credentials."""
    
    try:
        console.print("[blue]🔐 Setting up Azure credentials...[/blue]")
        
        # Initialize credential manager
        cred_mgr = CredentialManager()
        
        # Store credentials
        cred_mgr.setup_azure_credentials(tenant_id, client_id, client_secret, subscription_id)
        
        # Validate credentials
        if cred_mgr.validate_credentials("azure"):
            console.print(Panel.fit(
                "[bold green]✓ Azure credentials configured successfully[/bold green]\n\n"
                f"Tenant ID: {tenant_id}\n"
                f"Client ID: {client_id}\n"
                f"Subscription ID: {subscription_id}\n"
                f"Validation: ✓ Passed",
                title="Azure Credentials",
                border_style="green"
            ))
        else:
            console.print("[yellow]⚠ Credentials stored but validation failed[/yellow]")
            console.print("Please check your credentials and try again")
        
    except CredentialError as e:
        console.print(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def setup_gcp(
    service_account_key_path: str = typer.Option(
        ...,
        "--service-account-key-path",
        help="Path to GCP service account JSON key file"
    )
) -> None:
    """Setup GCP service account credentials."""
    
    try:
        console.print("[blue]🔐 Setting up GCP credentials...[/blue]")
        
        # Read service account key file
        key_path = Path(service_account_key_path)
        if not key_path.exists():
            console.print(f"[red]Error: Service account key file not found: {service_account_key_path}[/red]")
            raise typer.Exit(1)
        
        with open(key_path, 'r') as f:
            service_account_key = f.read()
        
        # Initialize credential manager
        cred_mgr = CredentialManager()
        
        # Store credentials
        cred_mgr.setup_gcp_credentials(service_account_key)
        
        # Validate credentials
        if cred_mgr.validate_credentials("gcp"):
            console.print(Panel.fit(
                "[bold green]✓ GCP credentials configured successfully[/bold green]\n\n"
                f"Service Account Key: {key_path.name}\n"
                f"Validation: ✓ Passed",
                title="GCP Credentials",
                border_style="green"
            ))
        else:
            console.print("[yellow]⚠ Credentials stored but validation failed[/yellow]")
            console.print("Please check your service account key and try again")
        
    except CredentialError as e:
        console.print(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list(
    show_values: bool = typer.Option(
        False,
        "--show-values",
        help="Show credential values (use with caution)"
    )
) -> None:
    """List stored credentials."""
    
    try:
        console.print("[blue]📋 Listing stored credentials...[/blue]")
        
        # Initialize credential manager
        cred_mgr = CredentialManager()
        
        # Get all credentials
        credentials = cred_mgr.list_credentials()
        
        if not credentials:
            console.print("[yellow]No credentials stored[/yellow]")
            return
        
        # Display credentials
        table = Table(title="Stored Credentials")
        table.add_column("Provider", style="cyan")
        table.add_column("Credential Type", style="green")
        table.add_column("Status", style="yellow")
        
        for provider, cred_types in credentials.items():
            for cred_type, status in cred_types.items():
                table.add_row(provider.capitalize(), cred_type, status)
        
        console.print(table)
        
        # Show values if requested
        if show_values:
            if Confirm.ask("⚠️  Are you sure you want to display credential values?"):
                console.print("\n[bold red]⚠️  Credential Values (Sensitive Data)[/bold red]")
                
                for provider in ["aws", "azure", "gcp"]:
                    provider_creds = {}
                    
                    if provider == "aws":
                        provider_creds = cred_mgr.get_aws_credentials()
                    elif provider == "azure":
                        provider_creds = cred_mgr.get_azure_credentials()
                    elif provider == "gcp":
                        provider_creds = cred_mgr.get_gcp_credentials()
                    
                    if provider_creds:
                        console.print(f"\n[bold]{provider.upper()} Credentials:[/bold]")
                        for key, value in provider_creds.items():
                            if key == "service_account_key":
                                console.print(f"  {key}: [REDACTED JSON KEY]")
                            else:
                                # Mask sensitive values
                                if "secret" in key.lower() or "key" in key.lower():
                                    masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                                    console.print(f"  {key}: {masked_value}")
                                else:
                                    console.print(f"  {key}: {value}")
        
    except CredentialError as e:
        console.print(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def validate(
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help="Specific provider to validate (aws, azure, gcp)"
    )
) -> None:
    """Validate stored credentials."""
    
    try:
        console.print("[blue]🔍 Validating credentials...[/blue]")
        
        # Initialize credential manager
        cred_mgr = CredentialManager()
        
        providers_to_check = ["aws", "azure", "gcp"]
        if provider:
            providers_to_check = [provider.lower()]
        
        table = Table(title="Credential Validation Results")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")
        
        for provider_name in providers_to_check:
            try:
                is_valid = cred_mgr.validate_credentials(provider_name)
                status = "✓ Valid" if is_valid else "✗ Invalid"
                status_color = "green" if is_valid else "red"
                
                details = "All required credentials present" if is_valid else "Missing or invalid credentials"
                
                table.add_row(provider_name.capitalize(), f"[{status_color}]{status}[/{status_color}]", details)
                
            except Exception as e:
                table.add_row(provider_name.capitalize(), "[red]✗ Error[/red]", str(e)[:50])
        
        console.print(table)
        
    except CredentialError as e:
        console.print(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def remove(
    provider: str = typer.Argument(..., help="Provider to remove credentials for (aws, azure, gcp)"),
    credential_type: Optional[str] = typer.Option(
        None,
        "--credential-type",
        help="Specific credential type to remove"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force removal without confirmation"
    )
) -> None:
    """Remove stored credentials."""
    
    try:
        provider = provider.lower()
        if provider not in ["aws", "azure", "gcp"]:
            console.print(f"[red]Error: Invalid provider '{provider}'. Use aws, azure, or gcp.[/red]")
            raise typer.Exit(1)
        
        # Initialize credential manager
        cred_mgr = CredentialManager()
        
        if credential_type:
            # Remove specific credential type
            if not force:
                if not Confirm.ask(f"Remove {credential_type} credential for {provider.upper()}?"):
                    console.print("Operation cancelled")
                    return
            
            cred_mgr.delete_credential(provider, credential_type)
            console.print(f"[green]✓ Removed {credential_type} credential for {provider.upper()}[/green]")
        else:
            # Remove all credentials for provider
            if not force:
                if not Confirm.ask(f"Remove ALL credentials for {provider.upper()}?"):
                    console.print("Operation cancelled")
                    return
            
            cred_mgr.clear_all_credentials()
            console.print(f"[green]✓ Removed all credentials for {provider.upper()}[/green]")
        
    except CredentialError as e:
        console.print(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def export(
    provider: str = typer.Argument(..., help="Provider to export credentials for (aws, azure, gcp)"),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output-file",
        "-o",
        help="Output file path (defaults to stdout)"
    )
) -> None:
    """Export credentials in environment variable format."""
    
    try:
        provider = provider.lower()
        if provider not in ["aws", "azure", "gcp"]:
            console.print(f"[red]Error: Invalid provider '{provider}'. Use aws, azure, or gcp.[/red]")
            raise typer.Exit(1)
        
        # Initialize credential manager
        cred_mgr = CredentialManager()
        
        # Get credentials
        if provider == "aws":
            creds = cred_mgr.get_aws_credentials()
            env_vars = {
                'AWS_ACCESS_KEY_ID': creds.get('access_key_id', ''),
                'AWS_SECRET_ACCESS_KEY': creds.get('secret_access_key', ''),
                'AWS_SESSION_TOKEN': creds.get('session_token', ''),
            }
        elif provider == "azure":
            creds = cred_mgr.get_azure_credentials()
            env_vars = {
                'AZURE_TENANT_ID': creds.get('tenant_id', ''),
                'AZURE_CLIENT_ID': creds.get('client_id', ''),
                'AZURE_CLIENT_SECRET': creds.get('client_secret', ''),
                'AZURE_SUBSCRIPTION_ID': creds.get('subscription_id', ''),
            }
        elif provider == "gcp":
            creds = cred_mgr.get_gcp_credentials()
            env_vars = {
                'GOOGLE_APPLICATION_CREDENTIALS': creds.get('service_account_key', ''),
            }
        
        # Format output
        output_lines = [f"# {provider.upper()} Environment Variables"]
        for key, value in env_vars.items():
            if value:
                output_lines.append(f"export {key}='{value}'")
            else:
                output_lines.append(f"# {key} not set")
        
        output_text = '\n'.join(output_lines)
        
        # Output to file or stdout
        if output_file:
            output_file.write_text(output_text)
            console.print(f"[green]✓ Exported {provider.upper()} credentials to {output_file}[/green]")
        else:
            console.print(f"\n[bold]{provider.upper()} Environment Variables:[/bold]")
            console.print(output_text)
        
    except CredentialError as e:
        console.print(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show credential system status."""
    
    try:
        console.print("[blue]🔐 Credential System Status[/blue]")
        
        # Initialize credential manager
        cred_mgr = CredentialManager()
        
        # Check encryption key
        try:
            cred_mgr._get_encryption_key()
            encryption_status = "✓ Configured"
            encryption_color = "green"
        except Exception:
            encryption_status = "✗ Not configured"
            encryption_color = "red"
        
        # Check each provider
        table = Table(title="Credential Status")
        table.add_column("Provider", style="cyan")
        table.add_column("Stored", style="green")
        table.add_column("Valid", style="yellow")
        table.add_column("Missing", style="red")
        
        for provider in ["aws", "azure", "gcp"]:
            try:
                # Check if credentials are stored
                stored_creds = cred_mgr.list_credentials()
                provider_stored = bool(stored_creds.get(provider, {}))
                
                # Check if credentials are valid
                is_valid = cred_mgr.validate_credentials(provider) if provider_stored else False
                
                # Determine missing credentials
                if provider == "aws":
                    required = ["access_key_id", "secret_access_key"]
                elif provider == "azure":
                    required = ["tenant_id", "client_id", "client_secret", "subscription_id"]
                elif provider == "gcp":
                    required = ["service_account_key"]
                
                stored_types = list(stored_creds.get(provider, {}).keys())
                missing = [req for req in required if req not in stored_types]
                
                stored_status = "✓ Yes" if provider_stored else "✗ No"
                valid_status = "✓ Yes" if is_valid else "✗ No"
                missing_text = ", ".join(missing) if missing else "None"
                
                table.add_row(
                    provider.capitalize(),
                    stored_status,
                    valid_status,
                    missing_text
                )
                
            except Exception as e:
                table.add_row(provider.capitalize(), "✗ Error", "✗ Error", str(e)[:30])
        
        console.print(table)
        
        # Show encryption status
        console.print(Panel.fit(
            f"Encryption Key: [{encryption_color}]{encryption_status}[/{encryption_color}]\n"
            f"Storage Method: Encrypted keyring\n"
            f"Security Level: High (AES-256 encryption)",
            title="Security Status",
            border_style="blue"
        ))
        
    except CredentialError as e:
        console.print(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def rotate(
    provider: str = typer.Argument(..., help="Provider to rotate credentials for (aws, azure, gcp)"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force rotation without confirmation"
    )
) -> None:
    """Rotate credentials (remove existing and setup new)."""
    
    try:
        provider = provider.lower()
        if provider not in ["aws", "azure", "gcp"]:
            console.print(f"[red]Error: Invalid provider '{provider}'. Use aws, azure, or gcp.[/red]")
            raise typer.Exit(1)
        
        console.print(f"[blue]🔄 Rotating {provider.upper()} credentials...[/blue]")
        
        # Remove existing credentials
        cred_mgr = CredentialManager()
        
        if not force:
            if not Confirm.ask(f"This will remove all existing {provider.upper()} credentials. Continue?"):
                console.print("Operation cancelled")
                return
        
        cred_mgr.clear_all_credentials()
        console.print(f"[yellow]✓ Removed existing {provider.upper()} credentials[/yellow]")
        
        # Setup new credentials based on provider
        if provider == "aws":
            console.print("\n[bold]Setup new AWS credentials:[/bold]")
            access_key_id = Prompt.ask("Access Key ID")
            secret_access_key = getpass.getpass("Secret Access Key: ")
            session_token = Prompt.ask("Session Token (optional)", default="", show_default=False)
            
            if session_token:
                cred_mgr.setup_aws_credentials(access_key_id, secret_access_key, session_token)
            else:
                cred_mgr.setup_aws_credentials(access_key_id, secret_access_key)
        
        elif provider == "azure":
            console.print("\n[bold]Setup new Azure credentials:[/bold]")
            tenant_id = Prompt.ask("Tenant ID")
            client_id = Prompt.ask("Client ID")
            client_secret = getpass.getpass("Client Secret: ")
            subscription_id = Prompt.ask("Subscription ID")
            
            cred_mgr.setup_azure_credentials(tenant_id, client_id, client_secret, subscription_id)
        
        elif provider == "gcp":
            console.print("\n[bold]Setup new GCP credentials:[/bold]")
            key_path = Prompt.ask("Service Account Key File Path")
            
            setup_gcp(service_account_key_path=key_path)
            return
        
        # Validate new credentials
        if cred_mgr.validate_credentials(provider):
            console.print(f"[green]✓ {provider.upper()} credentials rotated successfully[/green]")
        else:
            console.print(f"[yellow]⚠ Credentials stored but validation failed[/yellow]")
        
    except CredentialError as e:
        console.print(f"[red]Credential error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(1)
