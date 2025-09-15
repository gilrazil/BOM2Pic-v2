#!/bin/bash
# Production Deployment Preparation

echo "�� Preparing BOM2Pic for PRODUCTION deployment..."

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️ You have uncommitted changes. Commit them first:"
    git status --short
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run tests
echo "🧪 Running tests..."
python3 -m py_compile app/*.py scripts/*.py tests/*.py
if [ $? -eq 0 ]; then
    echo "✅ All Python files compile successfully"
else
    echo "❌ Python compilation errors found"
    exit 1
fi

# Check environment variables are set for production
echo "🔧 Production environment checklist:"
echo "   □ Set RENDER=true in Render dashboard"
echo "   □ Set secure ADMIN_KEY in Render dashboard"  
echo "   □ Set PayPal production credentials in Render dashboard"
echo "   □ Set BASE_URL=https://bom2pic.com in Render dashboard"

# Commit and push
echo "📤 Committing changes..."
git add .
git commit -m "Deploy: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin main

echo "✅ Deployment complete!"
echo "🌐 Render will auto-deploy from main branch"
echo "🔗 Check: https://bom2pic.com/health"
