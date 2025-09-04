"""
Marketplace service
"""
import logging
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from src.db_core import get_session
from src.market.models import Template, TemplateVariant, TemplateAssets, TemplateGuidedSchema, TemplateBuilderState
from src.guided_prompt.engine import GuidedPromptEngine
from src.analytics.service import AnalyticsService

logger = logging.getLogger(__name__)

class MarketplaceService:
    """Marketplace service for template management"""
    
    def __init__(self):
        self.guided_engine = GuidedPromptEngine()
        self.analytics = AnalyticsService()
    
    def list_templates(self, category: Optional[str] = None, search: Optional[str] = None,
                       price_filter: Optional[str] = None, requires_plan: Optional[str] = None,
                       page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """List templates with filtering and pagination"""
        try:
            session = get_session()
            
            query = session.query(Template).filter(Template.is_public == True)
            
            # Apply filters
            if category:
                query = query.filter(Template.category == category)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        Template.name.ilike(search_term),
                        Template.short_desc.ilike(search_term),
                        Template.tags.contains([search])
                    )
                )
            
            if price_filter == 'free':
                query = query.filter(Template.price_cents.is_(None))
            elif price_filter == 'paid':
                query = query.filter(Template.price_cents.isnot(None))
            
            if requires_plan:
                query = query.filter(Template.requires_plan == requires_plan)
            
            # Count total
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            templates = query.order_by(desc(Template.created_at)).offset(offset).limit(per_page).all()
            
            # Format results
            result = []
            for template in templates:
                template_data = self._format_template(template)
                result.append(template_data)
            
            return {
                'templates': result,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
            
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return {'templates': [], 'total': 0, 'page': 1, 'per_page': per_page, 'pages': 0}
    
    def get_template(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get template by slug"""
        try:
            session = get_session()
            
            template = session.query(Template).filter(Template.slug == slug).first()
            
            if not template:
                return None
            
            return self._format_template(template, include_details=True)
            
        except Exception as e:
            logger.error(f"Error getting template {slug}: {e}")
            return None
    
    def plan_template(self, slug: str, guided_input: Dict[str, Any]) -> Dict[str, Any]:
        """Plan template using guided input"""
        try:
            session = get_session()
            
            template = session.query(Template).filter(Template.slug == slug).first()
            if not template:
                raise ValueError(f"Template {slug} not found")
            
            # Get guided schema
            guided_schema = session.query(TemplateGuidedSchema).filter(
                TemplateGuidedSchema.template_id == template.id
            ).first()
            
            if not guided_schema:
                raise ValueError(f"No guided schema found for template {slug}")
            
            # Validate guided input
            validated_input = self.guided_engine.validate_guided_input(
                guided_schema.schema, guided_input
            )
            
            # Get default builder state
            builder_state = session.query(TemplateBuilderState).filter(
                TemplateBuilderState.template_id == template.id,
                TemplateBuilderState.variant_id.is_(None)
            ).first()
            
            if not builder_state:
                raise ValueError(f"No builder state found for template {slug}")
            
            # Generate builder state from guided input
            generated_state = self.guided_engine.generate_builder_state(
                builder_state, validated_input
            )
            
            return {
                'template': self._format_template(template),
                'guided_input': validated_input,
                'builder_state': generated_state
            }
            
        except Exception as e:
            logger.error(f"Error planning template {slug}: {e}")
            raise
    
    def use_template(self, slug: str, guided_input: Dict[str, Any], 
                     variant_id: Optional[str] = None, tenant_id: str = None,
                     user_id: str = None) -> Dict[str, Any]:
        """Use template to create project and generate build"""
        try:
            session = get_session()
            
            template = session.query(Template).filter(Template.slug == slug).first()
            if not template:
                raise ValueError(f"Template {slug} not found")
            
            # Check if template requires subscription
            if template.requires_plan:
                # For now, just log the requirement
                logger.info(f"Template {slug} requires plan: {template.requires_plan}")
                # In the future, check actual subscription status
            
            # Get guided schema and validate input
            guided_schema = session.query(TemplateGuidedSchema).filter(
                TemplateGuidedSchema.template_id == template.id
            ).first()
            
            if guided_schema:
                validated_input = self.guided_engine.validate_guided_input(
                    guided_schema.schema, guided_input
                )
            else:
                validated_input = guided_input
            
            # Get builder state
            query = session.query(TemplateBuilderState).filter(
                TemplateBuilderState.template_id == template.id
            )
            
            if variant_id:
                query = query.filter(TemplateBuilderState.variant_id == variant_id)
            else:
                query = query.filter(TemplateBuilderState.variant_id.is_(None))
            
            builder_state = query.first()
            
            if not builder_state:
                raise ValueError(f"No builder state found for template {slug}")
            
            # Generate builder state
            generated_state = self.guided_engine.generate_builder_state(
                builder_state, validated_input
            )
            
            # Create project
            project_id = str(uuid.uuid4())
            project_slug = self._generate_project_slug(template.name, validated_input)
            
            # Save builder state
            try:
                from src.builder_api import save_builder_state
                save_result = save_builder_state(project_id, generated_state, tenant_id)
            except ImportError:
                # Fallback if builder API not available
                save_result = {'success': True, 'project_id': project_id}
            
            # Generate build
            try:
                from src.builder_api import generate_build
                build_result = generate_build(project_id, tenant_id)
            except ImportError:
                # Fallback if builder API not available
                build_result = {
                    'success': True,
                    'preview_url': f'/preview/{project_id}',
                    'preview_url_project': f'/ui/preview/{project_id}'
                }
            
            # Track analytics
            try:
                self.analytics.track(
                    tenant_id=tenant_id,
                    event='market.template.use.success',
                    user_id=user_id,
                    source='market',
                    props={
                        'template_slug': slug,
                        'template_name': template.name,
                        'project_id': project_id,
                        'variant_id': variant_id
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to track analytics: {e}")
            
            return {
                'success': True,
                'project_id': project_id,
                'project_slug': project_slug,
                'preview_url': build_result.get('preview_url', f'/preview/{project_id}'),
                'preview_url_project': build_result.get('preview_url_project', f'/ui/preview/{project_id}'),
                'template': self._format_template(template)
            }
            
        except Exception as e:
            logger.error(f"Error using template {slug}: {e}")
            
            # Track failure analytics
            try:
                self.analytics.track(
                    tenant_id=tenant_id,
                    event='market.template.use.error',
                    user_id=user_id,
                    source='market',
                    props={
                        'template_slug': slug,
                        'error': str(e)
                    }
                )
            except Exception:
                pass
            
            raise
    
    def create_template(self, template_data: Dict[str, Any], author_user_id: str) -> Dict[str, Any]:
        """Create a new template"""
        try:
            session = get_session()
            
            # Check if slug already exists
            existing = session.query(Template).filter(Template.slug == template_data['slug']).first()
            if existing:
                raise ValueError(f"Template with slug '{template_data['slug']}' already exists")
            
            # Create template
            template = Template(
                slug=template_data['slug'],
                name=template_data['name'],
                short_desc=template_data.get('short_desc', ''),
                long_desc=template_data.get('long_desc', ''),
                category=template_data['category'],
                tags=template_data.get('tags', []),
                price_cents=template_data.get('price_cents'),
                requires_plan=template_data.get('requires_plan'),
                author_user_id=author_user_id,
                is_public=template_data.get('is_public', False)
            )
            
            session.add(template)
            session.flush()  # Get the ID
            
            # Create guided schema if provided
            if 'guided_schema' in template_data:
                guided_schema = TemplateGuidedSchema(
                    template_id=template.id,
                    schema=template_data['guided_schema']
                )
                session.add(guided_schema)
            
            # Create assets if provided
            if 'assets' in template_data:
                assets = TemplateAssets(
                    template_id=template.id,
                    cover_image_url=template_data['assets'].get('cover_image_url'),
                    gallery=template_data['assets'].get('gallery', []),
                    sample_screens=template_data['assets'].get('sample_screens', [])
                )
                session.add(assets)
            
            # Create builder state if provided
            if 'builder_state' in template_data:
                builder_state = TemplateBuilderState(
                    template_id=template.id,
                    builder_state=template_data['builder_state']
                )
                session.add(builder_state)
            
            session.commit()
            
            return self._format_template(template)
            
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            raise
    
    def publish_template(self, slug: str) -> bool:
        """Publish a template"""
        try:
            session = get_session()
            
            template = session.query(Template).filter(Template.slug == slug).first()
            if not template:
                return False
            
            template.is_public = True
            template.updated_at = datetime.utcnow()
            session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error publishing template {slug}: {e}")
            return False
    
    def unpublish_template(self, slug: str) -> bool:
        """Unpublish a template"""
        try:
            session = get_session()
            
            template = session.query(Template).filter(Template.slug == slug).first()
            if not template:
                return False
            
            template.is_public = False
            template.updated_at = datetime.utcnow()
            session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error unpublishing template {slug}: {e}")
            return False
    
    def _format_template(self, template: Template, include_details: bool = False) -> Dict[str, Any]:
        """Format template for API response"""
        session = get_session()
        
        result = {
            'id': str(template.id),
            'slug': template.slug,
            'name': template.name,
            'short_desc': template.short_desc,
            'category': template.category,
            'tags': template.tags or [],
            'price_cents': template.price_cents,
            'requires_plan': template.requires_plan,
            'author_user_id': template.author_user_id,
            'is_public': template.is_public,
            'created_at': template.created_at.isoformat(),
            'updated_at': template.updated_at.isoformat()
        }
        
        if include_details:
            result['long_desc'] = template.long_desc
            
            # Get guided schema
            guided_schema = session.query(TemplateGuidedSchema).filter(
                TemplateGuidedSchema.template_id == template.id
            ).first()
            if guided_schema:
                result['guided_schema'] = guided_schema.schema
            
            # Get assets
            assets = session.query(TemplateAssets).filter(
                TemplateAssets.template_id == template.id
            ).first()
            if assets:
                result['assets'] = {
                    'cover_image_url': assets.cover_image_url,
                    'gallery': assets.gallery or [],
                    'sample_screens': assets.sample_screens or []
                }
        
        return result
    
    def _generate_project_slug(self, template_name: str, guided_input: Dict[str, Any]) -> str:
        """Generate project slug from template name and guided input"""
        # Use table_name if available, otherwise use template name
        base_name = guided_input.get('table_name', template_name.lower())
        
        # Convert to slug
        slug = re.sub(r'[^a-zA-Z0-9\s]', '', base_name.lower())
        slug = re.sub(r'\s+', '-', slug)
        
        # Add timestamp to ensure uniqueness
        timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        
        return f"{slug}-{timestamp}"
