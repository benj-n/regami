"""
Regami Admin CLI Tool

Command-line interface for user and dog profile management.

Usage:
	python -m app.admin_cli users list
	python -m app.admin_cli users deactivate <email>
	python -m app.admin_cli dogs list --owner-email <email>
	python -m app.admin_cli dogs delete <dog-id>
	python -m app.admin_cli content moderate --flagged
"""
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from sqlalchemy.orm import Session
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import SessionLocal
from app.models import User, Dog
from datetime import datetime

app = typer.Typer(help="Regami Admin CLI - Manage users, dogs, and content")
console = Console()

# Subcommands
users_app = typer.Typer(help="User management commands")
dogs_app = typer.Typer(help="Dog profile management commands")
content_app = typer.Typer(help="Content moderation commands")

app.add_typer(users_app, name="users")
app.add_typer(dogs_app, name="dogs")
app.add_typer(content_app, name="content")


def get_db():
	"""Get database session."""
	db = SessionLocal()
	try:
		return db
	except Exception as e:
		console.print(f"[red]Database connection failed: {e}[/red]")
		raise typer.Exit(code=1)


# ====================
# User Management
# ====================

@users_app.command("list")
def list_users(
	limit: int = typer.Option(10, help="Number of users to show"),
	active_only: bool = typer.Option(False, help="Show only active users"),
):
	"""List all users."""
	db = get_db()

	query = db.query(User)
	if active_only:
		query = query.filter(User.is_active == True)  # noqa: E712

	users = query.limit(limit).all()

	table = Table(title=f"Users (showing {len(users)})")
	table.add_column("ID", style="cyan")
	table.add_column("Email", style="green")
	table.add_column("Name", style="yellow")
	table.add_column("Active", style="magenta")
	table.add_column("Created", style="blue")

	for user in users:
		table.add_row(
			str(user.id),
			user.email,
			user.name or "N/A",
			"✓" if user.is_active else "✗",
			user.created_at.strftime("%Y-%m-%d") if user.created_at else "N/A"
		)

	console.print(table)
	db.close()


@users_app.command("info")
def user_info(email: str = typer.Argument(..., help="User email address")):
	"""Get detailed user information."""
	db = get_db()

	user = db.query(User).filter(User.email == email).first()
	if not user:
		console.print(f"[red]User not found: {email}[/red]")
		raise typer.Exit(code=1)

	# Get user's dogs
	dogs = db.query(Dog).filter(Dog.owner_id == user.id).all()

	console.print(f"\n[bold cyan]User Information[/bold cyan]")
	console.print(f"ID: {user.id}")
	console.print(f"Email: {user.email}")
	console.print(f"Name: {user.name or 'N/A'}")
	console.print(f"Phone: {user.phone or 'N/A'}")
	console.print(f"Active: {'Yes' if user.is_active else 'No'}")
	console.print(f"Created: {user.created_at}")
	console.print(f"Location: {user.location_address or 'N/A'}")
	console.print(f"FCM Token: {'Set' if user.fcm_token else 'Not set'}")
	console.print(f"\n[bold cyan]Dog Profiles ({len(dogs)})[/bold cyan]")

	for dog in dogs:
		console.print(f"  • {dog.name} (ID: {dog.id}) - {dog.breed or 'Unknown breed'}")

	db.close()


@users_app.command("deactivate")
def deactivate_user(
	email: str = typer.Argument(..., help="User email to deactivate"),
	reason: Optional[str] = typer.Option(None, help="Reason for deactivation"),
):
	"""Deactivate a user account."""
	db = get_db()

	user = db.query(User).filter(User.email == email).first()
	if not user:
		console.print(f"[red]User not found: {email}[/red]")
		raise typer.Exit(code=1)

	if not user.is_active:
		console.print(f"[yellow]User is already deactivated: {email}[/yellow]")
		db.close()
		return

	# Confirm action
	confirm = typer.confirm(f"Are you sure you want to deactivate {email}?")
	if not confirm:
		console.print("[yellow]Cancelled[/yellow]")
		db.close()
		return

	user.is_active = False
	db.commit()

	console.print(f"[green]✓ User deactivated: {email}[/green]")
	if reason:
		console.print(f"Reason: {reason}")

	# Log action (in production, this should go to audit log)
	console.print(f"[dim]Action logged at {datetime.utcnow()}[/dim]")

	db.close()


@users_app.command("activate")
def activate_user(email: str = typer.Argument(..., help="User email to activate")):
	"""Reactivate a deactivated user account."""
	db = get_db()

	user = db.query(User).filter(User.email == email).first()
	if not user:
		console.print(f"[red]User not found: {email}[/red]")
		raise typer.Exit(code=1)

	if user.is_active:
		console.print(f"[yellow]User is already active: {email}[/yellow]")
		db.close()
		return

	user.is_active = True
	db.commit()

	console.print(f"[green]✓ User activated: {email}[/green]")
	db.close()


# ====================
# Dog Profile Management
# ====================

@dogs_app.command("list")
def list_dogs(
	owner_email: Optional[str] = typer.Option(None, help="Filter by owner email"),
	limit: int = typer.Option(10, help="Number of dogs to show"),
):
	"""List dog profiles."""
	db = get_db()

	query = db.query(Dog).join(User)

	if owner_email:
		query = query.filter(User.email == owner_email)

	dogs = query.limit(limit).all()

	table = Table(title=f"Dog Profiles (showing {len(dogs)})")
	table.add_column("ID", style="cyan")
	table.add_column("Name", style="green")
	table.add_column("Breed", style="yellow")
	table.add_column("Age", style="magenta")
	table.add_column("Owner", style="blue")

	for dog in dogs:
		owner = db.query(User).filter(User.id == dog.owner_id).first()
		table.add_row(
			str(dog.id),
			dog.name,
			dog.breed or "Unknown",
			f"{dog.age_years}y" if dog.age_years else "N/A",
			owner.email if owner else "Unknown"
		)

	console.print(table)
	db.close()


@dogs_app.command("info")
def dog_info(dog_id: int = typer.Argument(..., help="Dog profile ID")):
	"""Get detailed dog profile information."""
	db = get_db()

	dog = db.query(Dog).filter(Dog.id == dog_id).first()
	if not dog:
		console.print(f"[red]Dog profile not found: {dog_id}[/red]")
		raise typer.Exit(code=1)

	owner = db.query(User).filter(User.id == dog.owner_id).first()

	console.print(f"\n[bold cyan]Dog Profile[/bold cyan]")
	console.print(f"ID: {dog.id}")
	console.print(f"Name: {dog.name}")
	console.print(f"Breed: {dog.breed or 'Unknown'}")
	console.print(f"Age: {dog.age_years} years, {dog.age_months} months")
	console.print(f"Sex: {dog.sex or 'Unknown'}")
	console.print(f"Size: {dog.size or 'Unknown'}")
	console.print(f"Temperament: {dog.temperament or 'N/A'}")
	console.print(f"Energy Level: {dog.energy_level or 'N/A'}")
	console.print(f"Good with Dogs: {'Yes' if dog.good_with_dogs else 'No'}")
	console.print(f"Good with Cats: {'Yes' if dog.good_with_cats else 'No'}")
	console.print(f"Good with Kids: {'Yes' if dog.good_with_kids else 'No'}")
	console.print(f"Vaccinated: {'Yes' if dog.vaccinated else 'Unknown'}")
	console.print(f"Neutered: {'Yes' if dog.neutered else 'Unknown'}")
	console.print(f"Photo: {dog.photo_url or 'No photo'}")
	console.print(f"Bio: {dog.bio or 'No bio'}")
	console.print(f"\n[bold cyan]Owner[/bold cyan]")
	if owner:
		console.print(f"Email: {owner.email}")
		console.print(f"Name: {owner.name or 'N/A'}")

	db.close()


@dogs_app.command("delete")
def delete_dog(
	dog_id: int = typer.Argument(..., help="Dog profile ID to delete"),
	reason: Optional[str] = typer.Option(None, help="Reason for deletion"),
):
	"""Delete a dog profile (use for inappropriate content)."""
	db = get_db()

	dog = db.query(Dog).filter(Dog.id == dog_id).first()
	if not dog:
		console.print(f"[red]Dog profile not found: {dog_id}[/red]")
		raise typer.Exit(code=1)

	# Show info before deleting
	console.print(f"\n[bold yellow]Profile to delete:[/bold yellow]")
	console.print(f"ID: {dog.id}")
	console.print(f"Name: {dog.name}")
	console.print(f"Owner ID: {dog.owner_id}")

	# Confirm action
	confirm = typer.confirm(f"Are you sure you want to delete this dog profile?")
	if not confirm:
		console.print("[yellow]Cancelled[/yellow]")
		db.close()
		return

	db.delete(dog)
	db.commit()

	console.print(f"[green]✓ Dog profile deleted: {dog_id}[/green]")
	if reason:
		console.print(f"Reason: {reason}")

	# Log action (in production, this should go to audit log)
	console.print(f"[dim]Action logged at {datetime.utcnow()}[/dim]")

	db.close()


# ====================
# Content Moderation
# ====================

@content_app.command("stats")
def content_stats():
	"""Show content statistics."""
	db = get_db()

	total_users = db.query(User).count()
	active_users = db.query(User).filter(User.is_active == True).count()
	total_dogs = db.query(Dog).count()

	console.print(f"\n[bold cyan]Content Statistics[/bold cyan]")
	console.print(f"Total Users: {total_users}")
	console.print(f"Active Users: {active_users}")
	console.print(f"Inactive Users: {total_users - active_users}")
	console.print(f"Total Dog Profiles: {total_dogs}")

	db.close()


@content_app.command("recent")
def recent_content(
	days: int = typer.Option(7, help="Number of days to look back"),
):
	"""Show recently created content."""
	db = get_db()

	from datetime import timedelta
	cutoff = datetime.utcnow() - timedelta(days=days)

	recent_users = db.query(User).filter(User.created_at >= cutoff).all()
	recent_dogs = db.query(Dog).filter(Dog.created_at >= cutoff).all()

	console.print(f"\n[bold cyan]Content Created in Last {days} Days[/bold cyan]")
	console.print(f"New Users: {len(recent_users)}")
	console.print(f"New Dog Profiles: {len(recent_dogs)}")

	if recent_users:
		console.print(f"\n[bold]Recent Users:[/bold]")
		for user in recent_users[:5]:  # Show first 5
			console.print(f"  • {user.email} - {user.created_at.strftime('%Y-%m-%d %H:%M')}")

	if recent_dogs:
		console.print(f"\n[bold]Recent Dog Profiles:[/bold]")
		for dog in recent_dogs[:5]:  # Show first 5
			owner = db.query(User).filter(User.id == dog.owner_id).first()
			console.print(f"  • {dog.name} by {owner.email if owner else 'Unknown'}")

	db.close()


if __name__ == "__main__":
	app()
