#!/bin/bash
# Build Lambda deployment package for Regami API

set -e

echo "🔨 Building Lambda deployment package..."

# Clean previous builds
rm -rf package lambda_deployment.zip

# Create package directory
mkdir -p package

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt -t package/

# Copy application code
echo "📋 Copying application code..."
cp -r app package/
cp lambda_handler.py package/

# Create ZIP file
echo "📦 Creating ZIP package..."
cd package
zip -r ../lambda_deployment.zip . -q
cd ..

# Check package size
SIZE=$(du -m lambda_deployment.zip | cut -f1)
echo "📏 Package size: ${SIZE}MB"

if [ $SIZE -gt 50 ]; then
    echo "❌ ERROR: Package too large (${SIZE}MB > 50MB Lambda limit)"
    echo "   Consider:"
    echo "   - Using Lambda Layers for large dependencies"
    echo "   - Removing unused dependencies"
    echo "   - Optimizing dependencies"
    exit 1
fi

echo "✅ Lambda package created successfully: lambda_deployment.zip"
echo ""
echo "📤 To deploy:"
echo "   aws lambda update-function-code \\"
echo "     --function-name regami-api \\"
echo "     --zip-file fileb://lambda_deployment.zip"
