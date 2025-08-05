#!/bin/bash

# Script to check and fix CSS file issues in the React app

echo "🎨 Checking CSS files in public/css directory..."

# Check if public/css exists
if [ ! -d "public/css" ]; then
    echo "❌ public/css directory not found! Creating it..."
    mkdir -p public/css
fi

# List current CSS files
echo ""
echo "📁 Current CSS files in public/css:"
ls -la public/css/ 2>/dev/null || echo "No files found"

# Check if main.css exists
if [ ! -f "public/css/main.css" ]; then
    echo ""
    echo "❌ main.css not found! Creating a basic one..."
    
    # Create a complete main.css with all styles inline (temporary fix)
    cat > public/css/main.css << 'EOF'
/* Temporary consolidated CSS for React Threat Modeling App */

/* CSS Variables */
:root {
  /* Colors */
  --bg-primary: #0a0e1a;
  --bg-secondary: #1e293b;
  --bg-surface: #334155;
  --bg-tertiary: #475569;
  
  --text-primary: #f8fafc;
  --text-secondary: #e2e8f0;
  --text-muted: #94a3b8;
  
  --accent-color: #3b82f6;
  --success-color: #10b981;
  --warning-color: #f59e0b;
  --error-color: #ef4444;
  
  --border-color: #334155;
  
  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  
  /* Layout */
  --sidebar-width: 280px;
  --sidebar-collapsed-width: 60px;
  
  /* Z-index */
  --z-modal: 1050;
  --z-fixed: 1030;
  --z-sticky: 1020;
  
  /* Transitions */
  --transition-base: 0.2s ease;
  --transition-fast: 0.15s ease;
}

/* Global Styles */
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: var(--bg-primary);
  color: var(--text-primary);
}

/* Layout */
.app-container {
  display: flex;
  min-height: 100vh;
}

.main-content {
  flex: 1;
  margin-left: var(--sidebar-width);
  padding: var(--spacing-xl);
  transition: margin-left var(--transition-base);
}

.main-content.sidebar-collapsed {
  margin-left: var(--sidebar-collapsed-width);
}

/* Sidebar */
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
  color: var(--text-primary);
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
  transition: opacity var(--transition-base);
}

.sidebar.collapsed .sidebar-header h1 {
  opacity: 0;
}

.sidebar-header p {
  margin: 0 0 var(--spacing-lg) 0;
  font-size: 0.75rem;
  color: var(--text-muted);
  transition: opacity var(--transition-base);
}

.sidebar.collapsed .sidebar-header p {
  opacity: 0;
}

/* Pipeline Steps */
.pipeline-steps {
  margin-bottom: var(--spacing-lg);
}

.step-item {
  display: flex;
  align-items: center;
  padding: var(--spacing-sm) var(--spacing-md);
  margin-bottom: var(--spacing-xs);
  border-radius: 0.375rem;
  cursor: pointer;
  transition: all var(--transition-fast);
  color: var(--text-secondary);
  gap: var(--spacing-sm);
}

.step-item:hover {
  background-color: var(--bg-surface);
}

.step-item.active {
  background-color: var(--accent-color);
  color: white;
}

.step-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.step-name {
  transition: opacity var(--transition-base);
}

.sidebar.collapsed .step-name {
  opacity: 0;
  width: 0;
  overflow: hidden;
}

/* Upload Zone */
.upload-zone {
  border: 2px dashed var(--border-color);
  border-radius: 0.5rem;
  padding: var(--spacing-xl);
  text-align: center;
  background-color: var(--bg-secondary);
  cursor: pointer;
  transition: all var(--transition-base);
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.upload-zone:hover {
  border-color: var(--accent-color);
  background-color: var(--bg-surface);
}

.upload-zone.drag-over {
  border-color: var(--success-color);
  background-color: rgba(16, 185, 129, 0.1);
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-md);
  opacity: 0.6;
}

/* Buttons */
.btn {
  padding: var(--spacing-sm) var(--spacing-md);
  border: none;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.btn-primary {
  background-color: var(--accent-color);
  color: white;
}

.btn-primary:hover {
  background-color: #2563eb;
}

.btn-secondary {
  background-color: var(--bg-surface);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background-color: var(--bg-tertiary);
}

/* Cards */
.card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.card-header {
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.card-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
}

/* Status Badge */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  gap: var(--spacing-xs);
}

.status-badge.connected {
  background-color: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
}

.status-badge.disconnected {
  background-color: rgba(239, 68, 68, 0.1);
  color: var(--error-color);
}

/* Notifications */
.notification-container {
  position: fixed;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  z-index: var(--z-modal);
  max-width: 400px;
}

.notification {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  animation: slideInRight 0.3s ease-out;
}

.notification-content {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
}

.notification-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.notification.success .notification-icon {
  color: var(--success-color);
}

.notification.error .notification-icon {
  color: var(--error-color);
}

.notification.warning .notification-icon {
  color: var(--warning-color);
}

.notification.info .notification-icon {
  color: var(--accent-color);
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

/* Step Content Display */
.step-content-display {
  padding: var(--spacing-lg);
  background-color: var(--bg-surface);
  border-radius: 0.5rem;
  border: 1px solid var(--border-color);
}

.step-header {
  text-align: center;
  margin-bottom: var(--spacing-lg);
}

.step-title {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.step-description {
  margin: 0;
  color: var(--text-muted);
}

/* Empty States */
.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-muted);
}

.empty-state-icon {
  font-size: 3rem;
  opacity: 0.3;
  margin-bottom: var(--spacing-md);
}

/* Loading States */
.loading {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--text-muted);
}

.spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Responsive */
@media (max-width: 768px) {
  .sidebar {
    width: var(--sidebar-collapsed-width);
  }
  
  .main-content {
    margin-left: var(--sidebar-collapsed-width);
    padding: var(--spacing-md);
  }
  
  .sidebar-header h1,
  .sidebar-header p,
  .step-name {
    opacity: 0;
    width: 0;
    overflow: hidden;
  }
}
EOF
    echo "✅ Created main.css with consolidated styles"
else
    echo "✅ main.css exists"
fi

# Check for other CSS files that main.css might be importing
CSS_FILES=("base.css" "sidebar.css" "components.css" "pipeline-steps.css" "notifications.css" "review-system.css" "utilities.css" "settings-styles.css")

echo ""
echo "📋 Checking for imported CSS files..."
for file in "${CSS_FILES[@]}"; do
    if [ ! -f "public/css/$file" ]; then
        echo "❌ Missing: $file"
    else
        echo "✅ Found: $file"
    fi
done

# Create a simple test to see if CSS is loading
echo ""
echo "🔍 To debug CSS loading:"
echo "1. Open browser DevTools (F12)"
echo "2. Go to Network tab"
echo "3. Refresh the page"
echo "4. Check if main.css is loading (should show 200 status)"
echo "5. Check Console for any CSS-related errors"

echo ""
echo "🎯 Quick fix applied!"
echo "The app should now have basic styling."
echo ""
echo "If you have the original CSS files in a backup, you can copy them:"
echo "cp backup/*/css/*.css public/css/"