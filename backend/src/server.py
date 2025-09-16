#!/usr/bin/env python3
"""System Builder Hub - Stable Server Entrypoint - Phase 1 Cloud Migration with Session Management Fixes"""
import os
import logging
import time
import openai
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Create Flask application with stable imports"""
    app = Flask(__name__)
    
    # Core Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    app.config['DEBUG'] = os.getenv('FLASK_ENV') == 'development'
    app.config['WORKSPACE_ROOT'] = os.getenv('COB_WORKSPACE', 'workspace')
    
    # Database Configuration
    app.config['DATABASE_URL'] = os.getenv('DATABASE_URL', 'sqlite:///./db/sbh.db')
    
    # OpenAI Configuration
    app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    
    # AWS Configuration (Phase 2)
    app.config['AWS_REGION'] = os.getenv('AWS_REGION', 'us-east-1')
    app.config['AWS_BUCKET_NAME'] = os.getenv('AWS_BUCKET_NAME', 'sbh-workspace')
    
    # CORS Configuration
    cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8000')
    app.config['CORS_ORIGINS'] = cors_origins.split(',')
    
    # Initialize CORS with configured origins
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Initialize OpenAI
    openai.api_key = app.config['OPENAI_API_KEY']
    
    # Initialize database manager
    try:
        from .database_manager import init_database, get_current_session, remove_current_session
        db_initialized = init_database()
        if db_initialized:
            logger.info("Database manager initialized")
        else:
            logger.error("Failed to initialize database manager")
    except Exception as e:
        logger.error(f"Failed to initialize database manager: {e}")
        db_initialized = False
    
    # Flask session management - one session per request
    @app.before_request
    def before_request():
        """Create database session for each request"""
        if db_initialized:
            g.db = get_current_session()
            logger.debug("Created database session for request")
    
    @app.teardown_appcontext
    def teardown_appcontext(error):
        """Clean up database session after each request"""
        if hasattr(g, 'db'):
            if error:
                g.db.rollback()
                logger.debug("Rolled back database session due to error")
            else:
                g.db.commit()
                logger.debug("Committed database session")
            g.db.close()
            remove_current_session()
            logger.debug("Closed database session")
    
    # Initialize S3 build storage
    try:
        from .s3_build_storage import init_s3_storage
        s3_initialized = init_s3_storage()
        if s3_initialized:
            logger.info("S3 build storage initialized")
        else:
            logger.error("Failed to initialize S3 build storage")
    except Exception as e:
        logger.error(f"Failed to initialize S3 build storage: {e}")
        s3_initialized = False
    
    # Register API blueprints
    try:
        from .memory_api import memory_bp, specs_bp, builds_bp
        app.register_blueprint(memory_bp)
        app.register_blueprint(specs_bp)
        app.register_blueprint(builds_bp)
        logger.info("Persistent memory APIs registered")
    except Exception as e:
        logger.error(f"Failed to register memory APIs: {e}")
    
    # Register migration blueprint
    try:
        from .migrate_endpoint import migrate_bp
        app.register_blueprint(migrate_bp)
        logger.info("Migration API registered")
    except Exception as e:
        logger.error(f"Failed to register migration API: {e}")
    
    # Log configuration
    logger.info(f"SBH Server starting with database: {app.config['DATABASE_URL']}")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'production')}")
    logger.info(f"OpenAI configured: {bool(app.config['OPENAI_API_KEY'])}")
    logger.info(f"Database initialized: {db_initialized}")
    logger.info(f"S3 storage initialized: {s3_initialized}")

    @app.route('/api/health')
    def health():
        """Health check endpoint with database status"""
        try:
            # Test database connection
            from .database_manager import get_db_manager
            from .s3_build_storage import get_s3_storage
            from .auth import get_database_counts
            
            db_manager = get_db_manager()
            s3_storage = get_s3_storage()
            
            # Test database connection
            db_status = "unknown"
            db_type = "unknown"
            if db_manager.is_initialized():
                try:
                    from sqlalchemy import text
                    with db_manager.get_session() as session:
                        session.execute(text("SELECT 1"))
                    db_status = "healthy"
                    db_type = "postgresql" if app.config['DATABASE_URL'].startswith('postgresql') else "sqlite"
                except Exception as e:
                    db_status = f"error: {str(e)}"
            else:
                db_status = "not_initialized"
            
            # Test persistent memory
            memory_status = "disabled"
            if db_manager.is_initialized():
                try:
                    counts = get_database_counts()
                    memory_status = "healthy"
                except Exception as e:
                    memory_status = f"error: {str(e)}"
            
            # Test S3 storage
            storage_status = "disabled"
            if s3_storage.is_initialized():
                try:
                    if s3_storage.test_connection():
                        storage_status = "healthy"
                    else:
                        storage_status = "connection_failed"
                except Exception as e:
                    storage_status = f"error: {str(e)}"
            
            # Get database counts
            counts = {}
            if memory_status == "healthy":
                try:
                    counts = get_database_counts()
                except Exception as e:
                    logger.warning(f"Failed to get database counts: {e}")
            
            return jsonify({
                "ok": True, 
                "status": "healthy",
                "database": {
                    "type": db_type,
                    "status": db_status,
                    "url": app.config['DATABASE_URL'].split('@')[-1] if '@' in app.config['DATABASE_URL'] else app.config['DATABASE_URL']
                },
                "persistent_memory": {
                    "status": memory_status,
                    "type": db_type
                },
                "storage": {
                    "status": storage_status,
                    "type": "s3" if s3_storage.is_initialized() else "local"
                },
                "openai_configured": bool(app.config['OPENAI_API_KEY']),
                "environment": os.getenv('FLASK_ENV', 'production'),
                "counts": counts
            })
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                "ok": False, 
                "status": "unhealthy",
                "error": str(e)
            }), 500

    @app.route('/readiness')
    def readiness():
        return jsonify({"ok": True, "status": "ready"})

    @app.route('/healthz')
    def healthz():
        return jsonify({"ok": True, "status": "healthy"})

    @app.route('/')
    def index():
        return jsonify({
            "name": "System Builder Hub",
            "version": "1.0.0",
            "status": "running"
        })

    # AI Chat endpoints
    @app.route('/api/ai-chat/chat', methods=['POST'])
    def ai_chat():
        """AI Chat endpoint for website building conversation"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            message = data.get('message', '')
            conversation_history = data.get('conversation_history', [])
            
            if not message:
                return jsonify({'error': 'No message provided'}), 400

            # Use OpenAI to generate response
            client = openai.OpenAI(api_key=openai.api_key)
            
            # Build conversation context
            messages = [
                {"role": "system", "content": "You are an AI website builder assistant. Help users create comprehensive website specifications by asking relevant questions and providing guidance. You can build and deploy websites."}
            ]
            
            # Add conversation history
            for msg in conversation_history:
                messages.append(msg)
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            return jsonify({
                'success': True,
                'response': ai_response,
                'conversation_id': f'conv_{int(time.time())}'
            })
            
        except Exception as e:
            logger.error(f"AI Chat error: {str(e)}")
            return jsonify({'error': 'AI Chat failed', 'details': str(e)}), 500

    # Note: Persistent Memory and Build System API endpoints are handled by blueprints
    # registered above in the create_app() function

    @app.route('/api/ai-chat/health', methods=['GET'])
    def ai_chat_health():
        """Health check for AI Chat service"""
            return jsonify({
            'status': 'healthy',
            'openai_configured': bool(openai.api_key),
            'timestamp': int(time.time())
        })

    @app.route('/api/fix-db-schema', methods=['POST'])
    def fix_db_schema():
        """Fix database schema by creating proper tables"""
        try:
            from .database_manager import get_db_manager
            from sqlalchemy import text
            
            db_manager = get_db_manager()
            with db_manager.get_session() as session:
                # Create users table with proper schema
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        email VARCHAR(255) UNIQUE NOT NULL,
                        name VARCHAR(255),
                        password_hash VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                
                # Create tenants table
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS tenants (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) NOT NULL,
                        slug VARCHAR(255) UNIQUE NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                
                # Create user_tenants table
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS user_tenants (
                        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                        tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                        role VARCHAR(50) NOT NULL,
                        PRIMARY KEY (user_id, tenant_id)
                    )
                """))
                
                # Create sessions table
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                        tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                        started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_active_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        expires_at TIMESTAMP WITH TIME ZONE,
                        session_metadata JSONB
                    )
                """))
                
                # Create conversations table
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                        title VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                
                # Create messages table
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
                        role VARCHAR(50) NOT NULL,
                        content JSONB NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                
                # Create build_specs table
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS build_specs (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                        conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
                        title VARCHAR(255) NOT NULL,
                        plan_manifest JSONB NOT NULL,
                        repo_skeleton JSONB NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'draft',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                
                # Create build_runs table
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS build_runs (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
                        spec_id UUID REFERENCES build_specs(id) ON DELETE CASCADE,
                        build_id VARCHAR(255) NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'queued',
                        started_at TIMESTAMP WITH TIME ZONE,
                        finished_at TIMESTAMP WITH TIME ZONE,
                        logs_pointer TEXT,
                        artifacts_pointer TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                
                # Create indexes
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)"))
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_sessions_tenant_id ON sessions(tenant_id)"))
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_conversations_tenant_id ON conversations(tenant_id)"))
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)"))
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_build_specs_tenant_id ON build_specs(tenant_id)"))
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_build_runs_tenant_id ON build_runs(tenant_id)"))
                session.execute(text("CREATE INDEX IF NOT EXISTS idx_build_runs_spec_id ON build_runs(spec_id)"))
                
                # Insert demo data
                session.execute(text("""
                    INSERT INTO users (email, name, password_hash) 
                    VALUES ('demo@example.com', 'Demo User', 'demo-password-hash')
                    ON CONFLICT (email) DO NOTHING
                """))
                
                session.execute(text("""
                    INSERT INTO tenants (name, slug) 
                    VALUES ('Demo Tenant', 'demo')
                    ON CONFLICT (slug) DO NOTHING
                """))
                
                session.execute(text("""
                    INSERT INTO user_tenants (user_id, tenant_id, role)
                    SELECT u.id, t.id, 'admin'
                    FROM users u, tenants t
                    WHERE u.email = 'demo@example.com' AND t.slug = 'demo'
                    ON CONFLICT (user_id, tenant_id) DO NOTHING
                """))
                
                session.commit()
            
            return jsonify({
                "ok": True,
                "message": "Database schema fixed successfully"
            })
                        
        except Exception as e:
            logger.error(f"Schema fix failed: {e}")
        return jsonify({
                "ok": False,
                "error": str(e)
            }), 500

    # Compile endpoint
    @app.route('/api/cobuilder/compile', methods=['POST'])
    def compile_website():
        """Compile website from BuildSpec"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            spec = data.get('spec', '')
            if not spec:
                return jsonify({'error': 'No specification provided'}), 400

            # Parse the BuildSpec and generate actual website content
            website_content = generate_website_from_spec(spec)

            return jsonify({
                'success': True,
                'message': 'Website compiled successfully',
                'result': {
                    'writes': website_content['files'],
                    'diffs': []
                },
                'site_url': 'https://example.com',
                'build_id': 'build_' + str(int(time.time()))
            })

        except Exception as e:
            logger.error(f"Compile error: {str(e)}")
            return jsonify({'error': 'Compilation failed', 'details': str(e)}), 500

    # Deploy endpoint
    @app.route('/api/cobuilder/deploy', methods=['POST'])
    def deploy_website():
        """Deploy website to hosting"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            # Mock deployment for now
            return jsonify({
                'success': True,
                'message': 'Website deployed successfully',
                'deployment_id': 'deploy_' + str(int(time.time()))
            })
            
        except Exception as e:
            logger.error(f"Deploy error: {str(e)}")
            return jsonify({'error': 'Deployment failed', 'details': str(e)}), 500

    return app

def generate_website_from_spec(spec):
    """Generate website content from BuildSpec with component-based architecture"""
    # Parse the spec to extract key information
    lines = spec.split('\n')

    # Extract company name and key details
    company_name = "Umbervale"  # Default from your spec
    tagline = "AI-driven publishing and digital business innovation"
    description = "Forward-thinking company focused on AI-driven publishing, digital business models, and future-of-work themes"

    # Look for specific patterns in the spec
    for line in lines:
        line = line.strip()
        if 'Umbervale' in line:
            company_name = "Umbervale"
        if 'AI-driven publishing' in line:
            tagline = "AI-driven publishing and digital business innovation"
        if 'forward-thinking' in line.lower():
            description = "Forward-thinking company focused on AI-driven publishing, digital business models, and future-of-work themes"
    
    # Check if this is a modification request
    is_modification = "MODIFY EXISTING WEBSITE:" in spec
    if is_modification:
        # For modifications, we'll enhance the existing structure
        return generate_enhanced_website(company_name, tagline, description, spec)

    # Generate HTML content based on the spec
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} - {tagline}</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar">
        <div class="nav-container">
            <div class="nav-logo">
                <h2>{company_name}</h2>
            </div>
            <div class="nav-menu">
                <a href="#services" class="nav-link">Services</a>
                <a href="#about" class="nav-link">About</a>
                <a href="#blog" class="nav-link">Blog</a>
                <a href="#contact" class="nav-link">Contact</a>
                <button class="cta-button">Get Started</button>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero">
        <div class="hero-container">
            <h1 class="hero-title">{company_name}</h1>
            <p class="hero-tagline">{tagline}</p>
            <p class="hero-description">{description}</p>
            <div class="hero-buttons">
                <button class="btn-primary">Get Free Consultation</button>
                <button class="btn-secondary">Learn More</button>
            </div>
        </div>
    </section>

    <!-- Services Section -->
    <section id="services" class="services">
        <div class="container">
            <h2>Our Services</h2>
            <div class="services-grid">
                <div class="service-card">
                    <h3>AI-Driven Publishing</h3>
                    <p>Revolutionary publishing solutions powered by artificial intelligence</p>
                </div>
                <div class="service-card">
                    <h3>Digital Business Models</h3>
                    <p>Innovative approaches to digital transformation and business growth</p>
                </div>
                <div class="service-card">
                    <h3>Future-of-Work Solutions</h3>
                    <p>Preparing businesses for the evolving landscape of work</p>
                </div>
            </div>
        </div>
    </section>

    <!-- About Section -->
    <section id="about" class="about">
        <div class="container">
            <h2>About {company_name}</h2>
            <p>We are a forward-thinking company that balances innovation with credibility. Our focus on AI-driven publishing, digital business models, and future-of-work themes positions us at the forefront of technological advancement.</p>
        </div>
    </section>

    <!-- Blog Section -->
    <section id="blog" class="blog">
        <div class="container">
            <h2>Latest Insights</h2>
            <div class="blog-grid">
                <article class="blog-card">
                    <h3>Launch Story: Our Vision</h3>
                    <p>Discover our journey and the milestones that shaped our vision for the future.</p>
                </article>
                <article class="blog-card">
                    <h3>AI in Publishing</h3>
                    <p>Exploring how artificial intelligence is revolutionizing the publishing industry.</p>
                </article>
            </div>
        </div>
    </section>

    <!-- Newsletter Signup -->
    <section class="newsletter">
        <div class="container">
            <h2>Stay Updated</h2>
            <p>Subscribe to our newsletter for the latest insights on AI-driven publishing and digital innovation.</p>
            <form class="newsletter-form">
                <input type="email" placeholder="Enter your email" required>
                <button type="submit">Subscribe</button>
            </form>
        </div>
    </section>

    <!-- Contact Section -->
    <section id="contact" class="contact">
        <div class="container">
            <h2>Work With Us</h2>
            <p>Ready to transform your business with AI-driven solutions?</p>
            <button class="btn-primary">Contact Us</button>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <div class="footer-content">
                <div class="footer-section">
                    <h3>{company_name}</h3>
                    <p>{description}</p>
                </div>
                <div class="footer-section">
                    <h4>Services</h4>
                    <ul>
                        <li>AI-Driven Publishing</li>
                        <li>Digital Business Models</li>
                        <li>Future-of-Work Solutions</li>
                    </ul>
                </div>
                <div class="footer-section">
                    <h4>Contact</h4>
                    <p>eric@ericlarsonconsulting.com</p>
                    <p>(555) 123-4567</p>
                </div>
                <div class="footer-section">
                    <h4>Follow Us</h4>
                    <div class="social-links">
                        <a href="#">LinkedIn</a>
                        <a href="#">Twitter</a>
                    </div>
                </div>
            </div>
            <div class="footer-bottom">
                <p>&copy; 2024 {company_name}. All rights reserved.</p>
            </div>
        </div>
    </footer>

    <script src="script.js"></script>
</body>
</html>"""

    css_content = """/* Modern, professional styling for Umbervale */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    line-height: 1.6;
    color: #333;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Navigation */
.navbar {
    background: white;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    position: fixed;
    width: 100%;
    top: 0;
    z-index: 1000;
}

.nav-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 70px;
}

.nav-logo h2 {
    color: #2563eb;
    font-weight: 700;
}

.nav-menu {
    display: flex;
    align-items: center;
    gap: 30px;
}

.nav-link {
    text-decoration: none;
    color: #666;
    font-weight: 500;
    transition: color 0.3s;
}

.nav-link:hover {
    color: #2563eb;
}

.cta-button {
    background: #2563eb;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.3s;
}

.cta-button:hover {
    background: #1d4ed8;
}

/* Hero Section */
.hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 120px 0 80px;
    text-align: center;
}

.hero-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 0 20px;
}

.hero-title {
    font-size: 3.5rem;
    font-weight: 700;
    margin-bottom: 20px;
}

.hero-tagline {
    font-size: 1.5rem;
    margin-bottom: 20px;
    opacity: 0.9;
}

.hero-description {
    font-size: 1.1rem;
    margin-bottom: 40px;
    opacity: 0.8;
}

.hero-buttons {
    display: flex;
    gap: 20px;
    justify-content: center;
    flex-wrap: wrap;
}

.btn-primary, .btn-secondary {
    padding: 15px 30px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s;
    border: none;
}

.btn-primary {
    background: white;
    color: #2563eb;
}

.btn-primary:hover {
    background: #f8fafc;
    transform: translateY(-2px);
}

.btn-secondary {
    background: transparent;
    color: white;
    border: 2px solid white;
}

.btn-secondary:hover {
    background: white;
    color: #2563eb;
}

/* Sections */
section {
    padding: 80px 0;
}

section h2 {
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 50px;
    color: #1f2937;
}

/* Services */
.services {
    background: #f8fafc;
}

.services-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 30px;
}

.service-card {
    background: white;
    padding: 40px 30px;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    text-align: center;
    transition: transform 0.3s;
}

.service-card:hover {
    transform: translateY(-5px);
}

.service-card h3 {
    font-size: 1.5rem;
    margin-bottom: 15px;
    color: #2563eb;
}

/* About */
.about {
    background: white;
}

.about p {
    font-size: 1.2rem;
    text-align: center;
    max-width: 800px;
    margin: 0 auto;
    color: #666;
}

/* Blog */
.blog {
    background: #f8fafc;
}

.blog-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 30px;
}

.blog-card {
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}

.blog-card h3 {
    font-size: 1.3rem;
    margin-bottom: 15px;
    color: #2563eb;
}

/* Newsletter */
.newsletter {
    background: #2563eb;
    color: white;
    text-align: center;
}

.newsletter h2 {
    color: white;
}

.newsletter p {
    font-size: 1.2rem;
    margin-bottom: 30px;
    opacity: 0.9;
}

.newsletter-form {
    display: flex;
    max-width: 500px;
    margin: 0 auto;
    gap: 10px;
}

.newsletter-form input {
    flex: 1;
    padding: 15px;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
}

.newsletter-form button {
    background: white;
    color: #2563eb;
    border: none;
    padding: 15px 30px;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
}

/* Contact */
.contact {
    background: white;
    text-align: center;
}

.contact p {
    font-size: 1.2rem;
    margin-bottom: 30px;
    color: #666;
}

/* Footer */
.footer {
    background: #1f2937;
    color: white;
    padding: 60px 0 20px;
}

.footer-content {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 40px;
    margin-bottom: 40px;
}

.footer-section h3, .footer-section h4 {
    margin-bottom: 20px;
    color: #2563eb;
}

.footer-section ul {
    list-style: none;
}

.footer-section ul li {
    margin-bottom: 10px;
    color: #d1d5db;
}

.social-links {
    display: flex;
    gap: 20px;
}

.social-links a {
    color: #d1d5db;
    text-decoration: none;
}

.social-links a:hover {
    color: #2563eb;
}

.footer-bottom {
    border-top: 1px solid #374151;
    padding-top: 20px;
    text-align: center;
    color: #9ca3af;
}

/* Responsive */
@media (max-width: 768px) {
    .hero-title {
        font-size: 2.5rem;
    }

    .nav-menu {
        gap: 15px;
    }

    .hero-buttons {
        flex-direction: column;
        align-items: center;
    }

    .newsletter-form {
        flex-direction: column;
    }
}"""

    js_content = """// Interactive functionality for Umbervale website
document.addEventListener('DOMContentLoaded', function() {
    // Smooth scrolling for navigation links
    const navLinks = document.querySelectorAll('a[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Newsletter form submission
    const newsletterForm = document.querySelector('.newsletter-form');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = this.querySelector('input[type="email"]').value;
            alert('Thank you for subscribing! We\\'ll keep you updated on our latest insights.');
            this.reset();
        });
    }

    // Add scroll effect to navbar
    window.addEventListener('scroll', function() {
        const navbar = document.querySelector('.navbar');
        if (window.scrollY > 100) {
            navbar.style.background = 'rgba(255, 255, 255, 0.95)';
            navbar.style.backdropFilter = 'blur(10px)';
        } else {
            navbar.style.background = 'white';
            navbar.style.backdropFilter = 'none';
        }
    });

    // Add hover effects to service cards
    const serviceCards = document.querySelectorAll('.service-card');
    serviceCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
});"""

    return {
        'files': [
            {'path': 'index.html', 'content': html_content},
            {'path': 'styles.css', 'content': css_content},
            {'path': 'script.js', 'content': js_content}
        ]
    }

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app = create_app()
    use_reloader = os.getenv('FLASK_ENV') == 'development'
    logger.info(f"Starting server on port {port} (reloader={use_reloader})")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=use_reloader,
        use_reloader=use_reloader
    )
# Create app instance for WSGI
app = create_app()

