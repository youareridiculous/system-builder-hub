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

## 🚀 What SBH Can Do RIGHT NOW

### **1. AI-Powered System Generation**
- **Natural Language Input**: Describe your system in plain English
- **Real Code Generation**: Creates actual working code (not templates!)
- **Complete Systems**: Frontend + Backend + Infrastructure + CI/CD
- **24+ Files Generated**: Including React, Node.js, Terraform, Docker, GitHub Actions

### **2. System Preview & Testing**
- **Live Preview**: View generated code and architecture
- **System Validation**: Automated checks for completeness
- **Test Deployment**: Deploy to temporary environments
- **Download Ready**: Get complete ZIP packages

### **3. Production-Ready Infrastructure**
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
- Describe your system in natural language
- SBH generates complete, working code
- Preview, test, and download your system

### **Step 4: Deploy**
- Download the ZIP package
- Follow the included deployment instructions
- Your system is ready to run!

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
├── frontend/                 # Next.js + TypeScript
│   ├── package.json
│   ├── pages/index.tsx
│   ├── components/
│   └── tailwind.config.js
├── backend/                  # Node.js + Express
│   ├── package.json
│   ├── src/app.js
│   ├── src/models/
│   └── Dockerfile
├── infrastructure/           # Terraform
│   ├── main.tf
│   ├── variables.tf
│   └── modules/
├── .github/workflows/        # CI/CD
│   ├── deploy.yml
│   ├── test.yml
│   └── security.yml
└── README.md                 # Deployment instructions
```

**Total: 24+ files with real, working code!**

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

### **Phase 3: Advanced Features** (Coming Soon)
- **Live System Deployment**: Actually deploy generated systems to AWS
- **Real Database Schemas**: Generate actual SQL migrations
- **Environment Configuration**: Real `.env` files with proper secrets
- **Docker Compose**: Local development setup
- **API Documentation**: OpenAPI/Swagger specs

### **Phase 4: AI-Powered Architecture** (Future)
- **Architecture Analysis**: AI reviews and optimizes system design
- **Performance Recommendations**: Auto-suggest improvements
- **Security Scanning**: Built-in vulnerability detection
- **Cost Optimization**: AWS cost analysis and recommendations

## 🤝 Contributing

SBH is built to be the ultimate system builder. Contributions welcome!

## 📞 Support

- **Health Check**: https://sbh.umbervale.com/api/ai-chat/health
- **Frontend**: https://sbh.umbervale.com
- **Issues**: GitHub Issues

---

**SBH: Building the future, one system at a time.** 🚀
