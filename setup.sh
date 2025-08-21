#!/bin/bash

# MedQuery AI Setup Script
echo "🏥 Setting up MedQuery AI for VitaSense Health Solutions..."

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build the project
echo "🔨 Building the project..."
npm run build

# Create the dist directory if it doesn't exist
mkdir -p dist

echo "✅ Setup complete!"
echo ""
echo "🚀 To start the application, run:"
echo "   npm start"
echo ""
echo "🔧 For development mode, run:"
echo "   npm run dev"