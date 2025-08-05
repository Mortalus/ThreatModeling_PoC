#!/bin/bash

# Threat Model App - React Migration Setup Script
# This script sets up the React project structure and dependencies

echo "🛡️ Setting up React Threat Modeling App..."

# Create React app structure
echo "Creating React project structure..."

# Install dependencies for React development
npm install --save-dev @types/react @types/react-dom typescript @types/node

# Install runtime dependencies
npm install react react-dom

# Install additional dependencies for the threat modeling app
npm install socket.io-client chart.js d3 mermaid

# Install development dependencies
npm install --save-dev @typescript-eslint/eslint-plugin @typescript-eslint/parser eslint-plugin-react-hooks

# Create src directory structure
mkdir -p src/{components,hooks,services,types,utils,pages,context}
mkdir -p src/components/{common,pipeline,review,settings,sidebar}
mkdir -p public/{css,assets}

echo "✅ Project structure created!"

echo "📁 Directory structure:"
echo "src/"
echo "├── components/"
echo "│   ├── common/          # Reusable UI components"
echo "│   ├── pipeline/        # Pipeline-specific components"
echo "│   ├── review/          # Review system components"
echo "│   ├── settings/        # Settings modal components"
echo "│   └── sidebar/         # Sidebar components"
echo "├── hooks/               # Custom React hooks"
echo "├── services/            # API and external services"
echo "├── types/               # TypeScript type definitions"
echo "├── utils/               # Utility functions"
echo "├── pages/               # Page components"
echo "└── context/             # React context providers"

echo "🚀 Ready to begin React migration!"
echo "Next steps:"
echo "1. Run the migration script to convert components"
echo "2. Update imports and dependencies"
echo "3. Test all functionality"