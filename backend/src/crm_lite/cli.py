import click
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .seed import seed_crm_lite_data, seed_contacts
from src.db_core import get_database_url

logger = logging.getLogger(__name__)

def get_db_session():
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()

@click.group()
def crm_lite():
    """{name.title()} management commands"""
    pass

@crm_lite.command()
@click.option('--tenant', default='demo', help='Tenant ID for seeding')
def seed(tenant):
    """Seed demo data for crm_lite module"""
    seed_crm_lite_data(tenant)

@crm_lite.command()
@click.option('--tenant', default='demo', help='Tenant ID for seeding contacts')
def seed_contacts_cmd(tenant):
    """Seed demo contacts for crm_lite module"""
    seed_contacts(tenant)

@crm_lite.command()
@click.option('--tenant', default='demo', help='Tenant ID to check')
def status(tenant):
    """Check crm_lite module status"""
    logger.info(f"Checking crm_lite status for tenant: {tenant}")
    
    session = get_db_session()
    try:
        # TODO: Implement actual status checking
        logger.info(f"  TODO: Check crm_lite tables and data")
        logger.info(f"✅ crm_lite status check completed for tenant: {tenant}")
    except Exception as e:
        logger.error(f"Failed to check crm_lite status: {e}")
        raise
    finally:
        session.close()

@crm_lite.command()
@click.option('--tenant', default='demo', help='Tenant ID to reset')
def reset(tenant):
    """Reset crm_lite module data"""
    logger.info(f"Resetting crm_lite data for tenant: {tenant}")
    
    session = get_db_session()
    try:
        # TODO: Implement actual reset logic
        logger.info(f"  TODO: Reset crm_lite data for tenant {tenant}")
        logger.info(f"✅ crm_lite reset completed for tenant: {tenant}")
    except Exception as e:
        logger.error(f"Failed to reset crm_lite data: {e}")
        session.rollback()
        raise
    finally:
        session.close()
