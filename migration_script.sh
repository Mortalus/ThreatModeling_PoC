#!/bin/bash

# Threat Model App - React Migration Script
# This script migrates the vanilla JS/TS project to a proper React setup

set -e

echo "🛡️ Starting React Migration for Threat Modeling App..."
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    print_error "app.py not found. Please run this script from the project root directory."
    exit 1
fi

print_status "Detected threat modeling project structure"

# Backup existing files
print_status "Creating backup of existing files..."
mkdir -p backup/$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"

# Backup important files
cp -r js/ "$BACKUP_DIR/" 2>/dev/null || true
cp -r css/ "$BACKUP_DIR/" 2>/dev/null || true
cp index.html "$BACKUP_DIR/" 2>/dev/null || true
cp package*.json "$BACKUP_DIR/" 2>/dev/null || true

print_success "Backup created in $BACKUP_DIR"

# Create React app structure if it doesn't exist
if [ ! -f "package.json" ] || ! grep -q "react-scripts" package.json 2>/dev/null; then
    print_status "Setting up React project structure..."
    
    # Initialize if needed
    if [ ! -f "package.json" ]; then
        npm init -y
    fi
    
    # Install React dependencies
    print_status "Installing React dependencies..."
    npm install react@^18.2.0 react-dom@^18.2.0
    npm install --save-dev @types/react @types/react-dom typescript @types/node
    npm install --save-dev react-scripts
    
    # Install additional dependencies
    npm install socket.io-client chart.js react-chartjs-2 d3 mermaid date-fns lodash classnames
    npm install --save-dev @types/d3 @types/lodash
    
    # Install linting dependencies
    npm install --save-dev @typescript-eslint/eslint-plugin @typescript-eslint/parser eslint-plugin-react-hooks eslint-plugin-jsx-a11y eslint-plugin-import prettier
else
    print_status "React dependencies already installed"
fi

# Create src directory structure
print_status "Creating React source directory structure..."
mkdir -p src/{components,hooks,services,types,utils,pages,context}
mkdir -p src/components/{common,pipeline,review,settings,sidebar}
mkdir -p public/{css,assets}

# Move existing CSS files to public
if [ -d "css" ]; then
    print_status "Moving CSS files to public directory..."
    cp -r css/* public/css/ 2>/dev/null || true
fi

# Move assets if they exist
if [ -d "assets" ]; then
    print_status "Moving assets to public directory..."
    cp -r assets/* public/assets/ 2>/dev/null || true
fi

# Create or update public/index.html
print_status "Creating public/index.html..."
cat > public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="AI-Powered Threat Modeling Pipeline">
    <meta name="theme-color" content="#0a0e1a">
    <title>Advanced Threat Modeling Pipeline</title>
    
    <!-- External CDN resources for compatibility -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    
    <link rel="stylesheet" href="%PUBLIC_URL%/css/main.css">
</head>
<body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
</body>
</html>
EOF

# Create basic component stubs for missing components
print_status "Creating component stubs..."

# Error Boundary
cat > src/components/common/ErrorBoundary.tsx << 'EOF'
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <h1>Something went wrong.</h1>
          <details style={{ whiteSpace: 'pre-wrap' }}>
            {this.state.error && this.state.error.toString()}
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}
EOF

# Create CSS for notifications
cat > src/components/common/NotificationContainer.css << 'EOF'
.notification-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1080;
  max-width: 400px;
  width: 100%;
}

.notification {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: slideInRight 0.3s ease-out;
}

.notification-content {
  display: flex;
  align-items: flex-start;
  padding: var(--spacing-md);
}

.notification-icon {
  margin-right: var(--spacing-sm);
  font-size: 1.25rem;
  flex-shrink: 0;
}

.notification-message {
  flex: 1;
  color: var(--text-primary);
  line-height: 1.4;
}

.notification-dismiss {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1.25rem;
  padding: 0;
  margin-left: var(--spacing-sm);
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notification-progress {
  height: 3px;
  background: var(--bg-tertiary);
}

.notification-progress-bar {
  height: 100%;
  width: 100%;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}
EOF

# Create CSS for sidebar
cat > src/components/sidebar/CollapsibleSidebar.css << 'EOF'
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: var(--z-fixed);
  transition: all var(--transition-base);
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

.sidebar-toggle {
  position: absolute;
  top: 50%;
  right: -12px;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 1;
}

.sidebar-content {
  flex: 1;
  padding: var(--spacing-md);
  overflow-y: auto;
}

.sidebar-header h1 {
  margin: 0 0 var(--spacing-xs) 0;
  font-size: 1.125rem;
  font-weight: 600;
}

.sidebar-header p {
  margin: 0 0 var(--spacing-lg) 0;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.pipeline-steps {
  margin-bottom: var(--spacing-lg);
}
EOF

# Create stub components
mkdir -p src/components/{sidebar,pipeline,review,settings,common}

# Create basic stubs for major components
cat > src/components/sidebar/PipelineStep.tsx << 'EOF'
import React from 'react';

export const PipelineStep: React.FC<any> = (props) => {
  return <div>Pipeline Step Component - TODO: Implement</div>;
};
EOF

cat > src/components/sidebar/ConnectionStatus.tsx << 'EOF'
import React from 'react';

export const ConnectionStatus: React.FC<any> = (props) => {
  return <div>Connection Status Component - TODO: Implement</div>;
};
EOF

cat > src/components/sidebar/CollapsedStepIndicator.tsx << 'EOF'
import React from 'react';

export const CollapsedStepIndicator: React.FC<any> = (props) => {
  return <div>Collapsed Step Indicator - TODO: Implement</div>;
};
EOF

cat > src/components/pipeline/StepContentDisplay.tsx << 'EOF'
import React from 'react';

export const StepContentDisplay: React.FC<any> = (props) => {
  return <div>Step Content Display Component - TODO: Implement</div>;
};
EOF

cat > src/components/review/ReviewPanel.tsx << 'EOF'
import React from 'react';

export const ReviewPanel: React.FC<any> = (props) => {
  return <div>Review Panel Component - TODO: Implement</div>;
};
EOF

cat > src/components/common/ProgressDisplay.tsx << 'EOF'
import React from 'react';

export const ProgressDisplay: React.FC<any> = (props) => {
  return <div>Progress Display Component - TODO: Implement</div>;
};
EOF

cat > src/components/common/LoadingOverlay.tsx << 'EOF'
import React from 'react';

export const LoadingOverlay: React.FC<any> = (props) => {
  return <div>Loading Overlay Component - TODO: Implement</div>;
};
EOF

cat > src/components/settings/SettingsModal.tsx << 'EOF'
import React from 'react';

export const SettingsModal: React.FC<any> = (props) => {
  return <div>Settings Modal Component - TODO: Implement</div>;
};
EOF

# Create hook stubs
cat > src/hooks/usePipelineState.ts << 'EOF'
import { usePipelineState as originalHook } from '../context/PipelineStateContext';
export { originalHook as usePipelineState };
EOF

cat > src/hooks/useWebSocket.ts << 'EOF'
export { useWebSocket } from '../hooks/useWebSocket';
EOF

cat > src/hooks/useNotifications.ts << 'EOF'
export { useNotifications } from '../context/NotificationContext';
EOF

# Create basic index.css
cat > src/index.css << 'EOF'
/* Global styles imported from existing CSS structure */
@import url('../public/css/main.css');

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

code {
  font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New',
    monospace;
}
EOF

# Update package.json scripts
print_status "Updating package.json scripts..."
if command -v jq &> /dev/null; then
    # Use jq if available
    jq '.scripts.start = "react-scripts start" | 
        .scripts.build = "react-scripts build" | 
        .scripts.test = "react-scripts test" | 
        .scripts.eject = "react-scripts eject"' package.json > package.json.tmp && mv package.json.tmp package.json
else
    # Fallback: manual editing
    print_warning "jq not found, please manually update package.json scripts"
fi

# Create .env file for development
cat > .env << 'EOF'
# React App Configuration
REACT_APP_API_URL=http://localhost:5000
REACT_APP_WS_URL=ws://localhost:5000

# Development settings
GENERATE_SOURCEMAP=true
BROWSER=none
EOF

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    print_status "Creating .gitignore..."
    cat > .gitignore << 'EOF'
# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Production builds
build/
dist/

# Environment variables
.env.local
.env.development.local
.env.test.local
.env.production.local

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/

# Logs
logs/
*.log

# Runtime data
pids/
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/

# Dependency directories
jspm_packages/

# Optional npm cache directory
.npm

# Optional eslint cache
.eslintcache

# Backup directories
backup/
EOF
fi

# Final steps
print_status "Installing dependencies..."
npm install

print_success "React migration completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Review the generated src/ directory structure"
echo "2. Implement the component stubs created in src/components/"  
echo "3. Test the application with: npm start"
echo "4. Update any remaining vanilla JS components"
echo "5. Run the Flask backend: python app.py"
echo ""
echo "🔧 Development Commands:"
echo "  npm start          - Start development server"
echo "  npm run build      - Build for production"
echo "  npm run lint       - Run linting"
echo "  npm test           - Run tests"
echo ""
echo "📁 Backup Location: $BACKUP_DIR"
echo ""
print_success "Migration complete! Your React app is ready for development."
