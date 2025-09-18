# System Builder Hub (SBH) 🚀

**The AI-powered system that builds complete, deployable applications from natural language specifications.**

## 🎯 What is SBH?

SBH is an AI-assisted platform that takes high-level system specifications and outputs **complete, bootable applications** with their own infrastructure, CI/CD, and monitoring. Think of it as "better than Cursor" - it doesn't just write code, it builds entire systems.

## 🌟 Current Status: **LIVE & BEAST MODE**

**✅ FULLY OPERATIONAL**
- **Frontend**: https://sbh.umbervale.com (with authentication)
- **Backend API**: https://sbh.umbervale.com/api/ai-chat/health
- **Authentication**: Login required (admin@sbh.com / TempPass123!@#)
- **System Generation**: ✅ **WORKING** - Creates real, deployable systems
- **Persistent Storage**: ✅ **WORKING** - S3-based, survives container restarts
- **Preview/Test/Download**: ✅ **WORKING** - Full system lifecycle management
- **Edit & Regenerate**: ✅ **WORKING** - Iterative development workflow
- **File Upload & URL Analysis**: ✅ **WORKING** - Reference-based generation
- **Domain Management**: ✅ **WORKING** - Custom domain deployment
- **Live Deployment**: ✅ **WORKING** - Direct AWS deployment with URLs

## 🚀 What SBH Can Do RIGHT NOW

### **1. AI-Powered System Generation**
- **Natural Language Input**: Describe your system in plain English
- **Reference Integration**: Upload files, screenshots, documents, or provide URLs for AI analysis
- **Real Code Generation**: Creates actual working code (not templates!)
- **Complete Systems**: Frontend + Backend + Infrastructure + CI/CD
- **34+ Files Generated**: Including React, Node.js, Terraform, Docker, GitHub Actions, documentation

### **2. System Preview & Testing**
- **Live Preview**: View generated code and architecture
- **System Validation**: Automated checks for completeness
- **Test Deployment**: Deploy to temporary environments
- **Download Ready**: Get complete ZIP packages (22KB+ with full systems)

### **3. Iterative Development Workflow**
- **Edit Systems**: Modify specifications and regenerate components
- **Regenerate Components**: Update specific parts (templates, infrastructure, etc.)
- **Edit History Tracking**: Full audit trail of all changes
- **Live Feedback Loop**: Upload screenshots, errors, or feedback for AI fixes

### **4. Advanced File Analysis**
- **Image Analysis**: Upload screenshots for UI/UX reference
- **Document Processing**: PDF, Word docs, text files for requirements
- **URL Analysis**: Analyze existing websites for inspiration
- **Multi-format Support**: Handles various file types intelligently

### **5. Domain Management & Live Deployment**
- **Custom Domains**: Deploy to your own domain (e.g., `myapp.com`)
- **SBH Subdomains**: Use `myapp.sbh.umbervale.com` for quick deployment
- **DNS Management**: Automatic Route 53 setup for AWS domains
- **SSL Certificates**: Automatic HTTPS with AWS Certificate Manager
- **Live URLs**: Systems get real, accessible URLs immediately

### **6. Production-Ready Infrastructure**
- **AWS ECS Fargate**: Scalable container hosting
- **AWS RDS PostgreSQL**: Managed database
- **AWS S3**: Persistent storage for generated systems
- **AWS ALB + CloudFront**: Global content delivery
- **HTTPS + Custom Domain**: Professional setup

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Generated     │
│   (Next.js)     │◄──►│   (Flask)       │◄──►│   Systems       │
│   CloudFront    │    │   ECS Fargate   │    │   S3 Storage    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Authentication│    │   OpenAI API    │    │   AWS RDS       │
│   (Cognito)     │    │   Integration   │    │   PostgreSQL    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔐 Authentication

**Current Setup:**
- **Login Required**: All access requires authentication
- **Credentials**: 
  - Email: `admin@sbh.com`
  - Password: `TempPass123!@#`
- **Session Management**: Persistent login until logout

## 🎮 How to Use SBH

### **Step 1: Login**
Visit https://sbh.umbervale.com and login with the credentials above.

### **Step 2: Choose Your Mode**
- **Chat**: Talk to the AI about your system requirements
- **Builder**: Use the step-by-step system builder

### **Step 3: Generate Your System**
- **Describe your system** in natural language
- **Upload references** (optional): Screenshots, documents, or provide URLs
- **SBH analyzes** your requirements and references
- **Generates complete, working code** with 34+ files

### **Step 4: Preview & Test**
- **Preview** your generated system
- **Test** the system locally or in cloud
- **Download** the complete ZIP package

### **Step 5: Deploy Live**
- **Option A**: Download and deploy yourself
- **Option B**: Use SBH's live deployment
  - Choose custom domain or SBH subdomain
  - SBH handles DNS, SSL, and infrastructure
  - Get live URL immediately

### **Step 6: Iterate & Improve**
- **Edit** your system specifications
- **Upload feedback** (screenshots, errors, requirements)
- **Regenerate** specific components
- **Redeploy** with updates

## 🛠️ Technical Stack

### **Frontend**
- **Next.js 14** with TypeScript
- **Tailwind CSS** for styling
- **React 18** with modern hooks
- **Lucide React** for icons
- **AWS Cognito** for authentication

### **Backend**
- **Flask** with Python 3.11
- **OpenAI API** integration (GPT-4o, GPT-4o Mini, GPT-4 Turbo)
- **AWS S3** for persistent storage
- **Gunicorn** for production serving
- **CORS** enabled for frontend integration
- **File Analysis**: Pillow, BeautifulSoup4, PyPDF2, python-docx
- **Domain Management**: Route 53, ACM integration
- **Live Deployment**: ECS, ALB, CloudFront automation

### **Infrastructure**
- **AWS ECS Fargate** for container hosting
- **AWS RDS PostgreSQL** for database
- **AWS S3** for file storage
- **AWS ALB** for load balancing
- **AWS CloudFront** for CDN
- **AWS ACM** for SSL certificates
- **GitHub Actions** for CI/CD

## 📊 Generated System Example

When you generate a system, SBH creates:

```
your-system/
├── frontend/                 # React + TypeScript
│   ├── package.json
│   ├── src/App.tsx
│   ├── src/components/
│   ├── src/pages/
│   └── tailwind.config.js
├── backend/                  # Node.js + Express
│   ├── package.json
│   ├── src/app.js
│   ├── src/models/
│   ├── src/routes/
│   ├── src/middleware/
│   ├── database/migrations/
│   ├── scripts/
│   └── Dockerfile
├── deployment/               # CI/CD
│   ├── .github/workflows/
│   │   ├── deploy.yml
│   │   ├── test.yml
│   │   └── security.yml
├── docker/                   # Containerization
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── .env.example
├── infrastructure/           # Terraform
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
├── scripts/                  # Deployment Scripts
│   ├── deploy-aws.sh
│   ├── deploy-gcp.sh
│   └── deploy-azure.sh
└── docs/                     # Documentation
    ├── README.md
    ├── DEPLOYMENT.md
    └── API.md
```

**Total: 34+ files with real, working code!**

## 🔧 Configuration

### **Environment Variables**
- `OPENAI_API_KEY` - OpenAI API key (required)
- `OPENAI_MODEL` - Model selection (default: gpt-4o)
- `S3_BUCKET_NAME` - S3 bucket for system storage
- `SECRET_KEY` - Flask secret key
- `FLASK_ENV` - Environment (production/development)

### **AWS Resources**
- **ECS Cluster**: `sbh-cluster-dev`
- **ECS Service**: `sbh-service-dev`
- **S3 Bucket**: `sbh-generated-systems`
- **RDS Instance**: `sbh-db-dev`
- **ALB**: `sbh-alb-dev`

## 🚀 Deployment

### **Automatic Deployment**
- Push to `main` branch triggers build
- GitHub Actions builds and pushes to ECR
- ECS service automatically updates
- Health checks ensure successful deployment

### **Manual Deployment**
```bash
# Force new deployment
aws ecs update-service \
  --cluster sbh-cluster-dev \
  --service sbh-service-dev \
  --force-new-deployment
```

### **Verify Deployment**
```bash
curl -sS "https://sbh.umbervale.com/api/ai-chat/health" | jq .
```

## 📈 Monitoring

### **Health Checks**
- **Application**: `/api/ai-chat/health`
- **Load Balancer**: ALB health checks
- **ECS**: Service health via CloudWatch

### **Logs**
```bash
# View container logs
aws logs tail /ecs/sbh-backend --follow --since 1h
```

## 🔒 Security

- **HTTPS Only**: All traffic encrypted
- **Authentication Required**: Login for all access
- **AWS IAM**: Least privilege access
- **Secrets Management**: AWS Secrets Manager
- **Private Subnets**: Database and containers isolated
- **CORS Protection**: Configured for specific origins

## 🎯 What's Next?

### **Phase 3: Enhanced User Experience** (In Progress)
- **Visual System Builder**: Drag-and-drop interface for system design
- **Template Library**: Pre-built components and patterns
- **Collaboration Features**: Team sharing and version control
- **Advanced Analytics**: System performance and usage metrics

### **Phase 4: AI-Powered Architecture** (Future)
- **Architecture Analysis**: AI reviews and optimizes system design
- **Performance Recommendations**: Auto-suggest improvements
- **Security Scanning**: Built-in vulnerability detection
- **Cost Optimization**: AWS cost analysis and recommendations
- **Auto-scaling**: Intelligent resource management
- **Multi-cloud Support**: Deploy to GCP, Azure, and other providers

### **Phase 5: Enterprise Features** (Future)
- **White-label Solutions**: Custom branding and domains
- **Enterprise SSO**: SAML, OAuth integration
- **Compliance**: SOC2, HIPAA, GDPR compliance tools
- **Advanced Monitoring**: Custom dashboards and alerts

## 🤝 Contributing

SBH is built to be the ultimate system builder. Contributions welcome!

## 📞 Support

- **Health Check**: https://sbh.umbervale.com/api/ai-chat/health
- **Frontend**: https://sbh.umbervale.com
- **Issues**: GitHub Issues

## 🚀 API Endpoints

### **System Management**
- `POST /api/system/generate` - Generate new system
- `GET /api/system/preview/{id}` - Preview generated system
- `GET /api/system/download/{id}` - Download system ZIP
- `POST /api/system/edit/{id}` - Edit system specifications
- `POST /api/system/regenerate/{id}` - Regenerate system components
- `POST /api/system/deploy/{id}` - Deploy system to live URL

### **File & Reference Management**
- `POST /api/system/upload-reference/{id}` - Upload files for analysis
- `POST /api/system/analyze-url` - Analyze URL for reference

### **Domain Management**
- `POST /api/system/domain/validate` - Validate domain configuration
- `GET /api/system/domain/setup/{domain}` - Get domain setup instructions

### **Health & Status**
- `GET /api/ai-chat/health` - System health check

---

**SBH: Building the future, one system at a time.** 🚀
