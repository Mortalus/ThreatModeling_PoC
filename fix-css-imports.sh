#!/bin/bash

echo "Fixing all CSS import issues..."

# Create all the CSS files that main.css is trying to import

# 1. sidebar.css
echo "Creating sidebar.css..."
cat > src/css/sidebar.css << 'EOF'
/* Sidebar Layout Styles */
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width, 280px);
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: var(--z-sticky);
  transition: all var(--transition-base);
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width, 60px);
}

.sidebar-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.sidebar-header h1 {
  font-size: 1.5rem;
  margin: 0;
  font-weight: 600;
}

.sidebar-header p {
  margin: 0.5rem 0 0 0;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.sidebar-toggle {
  position: absolute;
  top: 50%;
  right: -12px;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-base);
}

.sidebar-toggle:hover {
  background-color: var(--bg-secondary);
  border-color: var(--accent-color);
}

.pipeline-steps {
  flex: 1;
  padding: var(--spacing-md);
  overflow-y: auto;
}

.step-item {
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.step-item:hover {
  background-color: rgba(59, 130, 246, 0.1);
  border-color: var(--accent-color);
}

.step-item.active {
  background-color: rgba(59, 130, 246, 0.2);
  border-color: var(--accent-color);
}

.step-item.completed {
  border-color: var(--success-color);
}

.step-icon {
  font-size: 1.5rem;
}

.step-content {
  flex: 1;
}

.step-name {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.step-status {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.collapsed .sidebar-header h1,
.collapsed .sidebar-header p,
.collapsed .step-name,
.collapsed .step-status {
  display: none;
}

.collapsed .step-item {
  justify-content: center;
}

.collapsed .step-content {
  display: none;
}
EOF

# 2. components.css
echo "Creating components.css..."
cat > src/css/components.css << 'EOF'
/* Component Styles */

/* Cards */
.card {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-sm);
}

.card-header {
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
}

.card-body {
  color: var(--text-secondary);
}

/* Progress Bar */
.progress-bar {
  width: 100%;
  height: 8px;
  background-color: var(--bg-surface);
  border-radius: 4px;
  overflow: hidden;
  margin: var(--spacing-sm) 0;
}

.progress-fill {
  height: 100%;
  background-color: var(--accent-color);
  transition: width 0.3s ease;
}

/* Badge */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 9999px;
  background-color: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.badge.success {
  background-color: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
  border-color: var(--success-color);
}

.badge.error {
  background-color: rgba(239, 68, 68, 0.1);
  color: var(--error-color);
  border-color: var(--error-color);
}

.badge.warning {
  background-color: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
  border-color: var(--warning-color);
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
  backdrop-filter: blur(4px);
}

.modal-content {
  background-color: var(--bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  max-width: 90%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-body {
  padding: var(--spacing-lg);
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
}

/* Tabs */
.tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: var(--spacing-lg);
}

.tab {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  position: relative;
  transition: all var(--transition-base);
}

.tab:hover {
  color: var(--text-primary);
}

.tab.active {
  color: var(--accent-color);
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background-color: var(--accent-color);
}

/* File Upload */
.file-upload {
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  text-align: center;
  transition: all var(--transition-base);
  cursor: pointer;
}

.file-upload:hover {
  border-color: var(--accent-color);
  background-color: rgba(59, 130, 246, 0.05);
}

.file-upload.dragging {
  border-color: var(--accent-color);
  background-color: rgba(59, 130, 246, 0.1);
}

.upload-icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-md);
  opacity: 0.5;
}

/* Data Viewer */
.data-viewer {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.data-viewer-header {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.data-viewer-content {
  padding: var(--spacing-md);
  overflow-x: auto;
}

.data-viewer pre {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.5;
}
EOF

# 3. pipeline-steps.css
echo "Creating pipeline-steps.css..."
cat > src/css/pipeline-steps.css << 'EOF'
/* Pipeline Steps Styles */
.pipeline-visualization {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  background-color: var(--bg-surface);
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-xl);
}

.pipeline-step {
  flex: 1;
  text-align: center;
  position: relative;
}

.pipeline-step:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 100%;
  width: 100%;
  height: 2px;
  background-color: var(--border-color);
  transform: translateY(-50%);
  z-index: 0;
}

.pipeline-step.completed:not(:last-child)::after {
  background-color: var(--success-color);
}

.step-circle {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background-color: var(--bg-secondary);
  border: 3px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--spacing-sm);
  position: relative;
  z-index: 1;
  transition: all var(--transition-base);
}

.pipeline-step.active .step-circle {
  border-color: var(--accent-color);
  background-color: var(--accent-color);
  color: white;
}

.pipeline-step.completed .step-circle {
  border-color: var(--success-color);
  background-color: var(--success-color);
  color: white;
}

.pipeline-step.error .step-circle {
  border-color: var(--error-color);
  background-color: var(--error-color);
  color: white;
}

.step-icon {
  font-size: 1.5rem;
}

.step-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.pipeline-step.active .step-label {
  color: var(--text-primary);
  font-weight: 500;
}
EOF

# 4. notifications.css
echo "Creating notifications.css..."
cat > src/css/notifications.css << 'EOF'
/* Notification Styles */
.notification-container {
  position: fixed;
  top: var(--spacing-lg);
  right: var(--spacing-lg);
  z-index: var(--z-modal);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.notification {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  box-shadow: var(--shadow-lg);
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  min-width: 300px;
  max-width: 500px;
  animation: slideInRight 0.3s ease;
}

.notification.success {
  border-color: var(--success-color);
}

.notification.error {
  border-color: var(--error-color);
}

.notification.warning {
  border-color: var(--warning-color);
}

.notification.info {
  border-color: var(--info-color);
}

.notification-icon {
  font-size: 1.25rem;
}

.notification-content {
  flex: 1;
}

.notification-title {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.notification-message {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.notification-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0;
  font-size: 1.25rem;
  line-height: 1;
  transition: color var(--transition-base);
}

.notification-close:hover {
  color: var(--text-primary);
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

# 5. review-system.css
echo "Creating review-system.css..."
cat > src/css/review-system.css << 'EOF'
/* Review System Styles */
.review-panel {
  background-color: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  padding: var(--spacing-lg);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.review-header {
  margin-bottom: var(--spacing-lg);
}

.review-title {
  font-size: 1.5rem;
  margin: 0 0 var(--spacing-sm) 0;
}

.review-stats {
  display: flex;
  gap: var(--spacing-md);
  font-size: 0.875rem;
}

.stat {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
}

.stat.pending {
  border-color: var(--warning-color);
  color: var(--warning-color);
}

.stat.approved {
  border-color: var(--success-color);
  color: var(--success-color);
}

.stat.rejected {
  border-color: var(--error-color);
  color: var(--error-color);
}

.review-controls {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.review-filters,
.review-sort {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.review-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.review-card {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  transition: all var(--transition-base);
}

.review-card:hover {
  border-color: var(--accent-color);
  box-shadow: var(--shadow-md);
}

.review-card.approved {
  border-color: var(--success-color);
}

.review-card.rejected {
  border-color: var(--error-color);
}

.review-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-md);
}

.item-info {
  display: flex;
  gap: var(--spacing-md);
}

.item-icon {
  font-size: 1.5rem;
}

.item-meta {
  flex: 1;
}

.item-title {
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
  font-weight: 500;
}

.item-timestamp {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  color: white;
}

.review-card-content {
  margin-bottom: var(--spacing-md);
}

.toggle-details {
  background: none;
  border: none;
  color: var(--accent-color);
  cursor: pointer;
  font-size: 0.875rem;
  padding: 0;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  transition: opacity var(--transition-base);
}

.toggle-details:hover {
  opacity: 0.8;
}

.item-details {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

.data-row {
  margin-bottom: var(--spacing-sm);
}

.data-row strong {
  margin-right: 0.5rem;
  color: var(--text-secondary);
}

.risk-badge {
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
}

.risk-low {
  background-color: rgba(16, 185, 129, 0.1);
  color: var(--success-color);
}

.risk-medium {
  background-color: rgba(245, 158, 11, 0.1);
  color: var(--warning-color);
}

.risk-high {
  background-color: rgba(239, 68, 68, 0.1);
  color: var(--error-color);
}

.risk-critical {
  background-color: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}

.review-actions {
  border-top: 1px solid var(--border-color);
  padding-top: var(--spacing-md);
}

.review-inputs {
  margin-bottom: var(--spacing-md);
}

.comments-input,
.modifications-input {
  width: 100%;
  margin-bottom: var(--spacing-sm);
}

.decision-buttons {
  display: flex;
  gap: var(--spacing-sm);
}

.review-empty {
  text-align: center;
  padding: var(--spacing-xl) var(--spacing-lg);
  color: var(--text-muted);
}

.empty-icon {
  font-size: 3rem;
  opacity: 0.3;
  margin-bottom: var(--spacing-md);
}
EOF

# 6. utilities.css
echo "Creating utilities.css..."
cat > src/css/utilities.css << 'EOF'
/* Utility Classes */

/* Display */
.d-none { display: none !important; }
.d-block { display: block !important; }
.d-flex { display: flex !important; }
.d-inline { display: inline !important; }
.d-inline-block { display: inline-block !important; }

/* Flexbox */
.flex-row { flex-direction: row !important; }
.flex-column { flex-direction: column !important; }
.justify-start { justify-content: flex-start !important; }
.justify-center { justify-content: center !important; }
.justify-end { justify-content: flex-end !important; }
.justify-between { justify-content: space-between !important; }
.align-start { align-items: flex-start !important; }
.align-center { align-items: center !important; }
.align-end { align-items: flex-end !important; }
.flex-wrap { flex-wrap: wrap !important; }
.flex-1 { flex: 1 !important; }
.gap-1 { gap: var(--spacing-xs) !important; }
.gap-2 { gap: var(--spacing-sm) !important; }
.gap-3 { gap: var(--spacing-md) !important; }
.gap-4 { gap: var(--spacing-lg) !important; }

/* Spacing */
.m-0 { margin: 0 !important; }
.m-1 { margin: var(--spacing-xs) !important; }
.m-2 { margin: var(--spacing-sm) !important; }
.m-3 { margin: var(--spacing-md) !important; }
.m-4 { margin: var(--spacing-lg) !important; }
.m-5 { margin: var(--spacing-xl) !important; }

.p-0 { padding: 0 !important; }
.p-1 { padding: var(--spacing-xs) !important; }
.p-2 { padding: var(--spacing-sm) !important; }
.p-3 { padding: var(--spacing-md) !important; }
.p-4 { padding: var(--spacing-lg) !important; }
.p-5 { padding: var(--spacing-xl) !important; }

/* Text */
.text-left { text-align: left !important; }
.text-center { text-align: center !important; }
.text-right { text-align: right !important; }
.text-justify { text-align: justify !important; }

.text-primary { color: var(--text-primary) !important; }
.text-secondary { color: var(--text-secondary) !important; }
.text-muted { color: var(--text-muted) !important; }
.text-success { color: var(--success-color) !important; }
.text-error { color: var(--error-color) !important; }
.text-warning { color: var(--warning-color) !important; }
.text-info { color: var(--info-color) !important; }

.font-weight-normal { font-weight: 400 !important; }
.font-weight-medium { font-weight: 500 !important; }
.font-weight-semibold { font-weight: 600 !important; }
.font-weight-bold { font-weight: 700 !important; }

.text-sm { font-size: 0.875rem !important; }
.text-base { font-size: 1rem !important; }
.text-lg { font-size: 1.125rem !important; }
.text-xl { font-size: 1.25rem !important; }
.text-2xl { font-size: 1.5rem !important; }

/* Background */
.bg-primary { background-color: var(--bg-primary) !important; }
.bg-secondary { background-color: var(--bg-secondary) !important; }
.bg-surface { background-color: var(--bg-surface) !important; }
.bg-success { background-color: var(--success-color) !important; }
.bg-error { background-color: var(--error-color) !important; }
.bg-warning { background-color: var(--warning-color) !important; }
.bg-info { background-color: var(--info-color) !important; }

/* Border */
.border-0 { border: 0 !important; }
.border { border: 1px solid var(--border-color) !important; }
.border-top { border-top: 1px solid var(--border-color) !important; }
.border-bottom { border-bottom: 1px solid var(--border-color) !important; }
.border-left { border-left: 1px solid var(--border-color) !important; }
.border-right { border-right: 1px solid var(--border-color) !important; }

.rounded-0 { border-radius: 0 !important; }
.rounded-sm { border-radius: var(--radius-sm) !important; }
.rounded { border-radius: var(--radius-md) !important; }
.rounded-lg { border-radius: var(--radius-lg) !important; }
.rounded-full { border-radius: 9999px !important; }

/* Width & Height */
.w-25 { width: 25% !important; }
.w-50 { width: 50% !important; }
.w-75 { width: 75% !important; }
.w-100 { width: 100% !important; }
.w-auto { width: auto !important; }

.h-25 { height: 25% !important; }
.h-50 { height: 50% !important; }
.h-75 { height: 75% !important; }
.h-100 { height: 100% !important; }
.h-auto { height: auto !important; }

/* Position */
.position-static { position: static !important; }
.position-relative { position: relative !important; }
.position-absolute { position: absolute !important; }
.position-fixed { position: fixed !important; }
.position-sticky { position: sticky !important; }

/* Visibility */
.visible { visibility: visible !important; }
.invisible { visibility: hidden !important; }

/* Overflow */
.overflow-auto { overflow: auto !important; }
.overflow-hidden { overflow: hidden !important; }
.overflow-scroll { overflow: scroll !important; }
.overflow-x-auto { overflow-x: auto !important; }
.overflow-y-auto { overflow-y: auto !important; }

/* Cursor */
.cursor-pointer { cursor: pointer !important; }
.cursor-default { cursor: default !important; }
.cursor-not-allowed { cursor: not-allowed !important; }

/* User Select */
.user-select-none { user-select: none !important; }
.user-select-text { user-select: text !important; }
.user-select-all { user-select: all !important; }

/* Transitions */
.transition-none { transition: none !important; }
.transition-all { transition: all var(--transition-base) !important; }
.transition-fast { transition: all var(--transition-fast) !important; }

/* Opacity */
.opacity-0 { opacity: 0 !important; }
.opacity-25 { opacity: 0.25 !important; }
.opacity-50 { opacity: 0.5 !important; }
.opacity-75 { opacity: 0.75 !important; }
.opacity-100 { opacity: 1 !important; }

/* Z-index */
.z-0 { z-index: 0 !important; }
.z-10 { z-index: 10 !important; }
.z-20 { z-index: 20 !important; }
.z-30 { z-index: 30 !important; }
.z-40 { z-index: 40 !important; }
.z-50 { z-index: 50 !important; }
EOF

# 7. settings-styles.css
echo "Creating settings-styles.css..."
cat > src/css/settings-styles.css << 'EOF'
/* Settings Modal Styles */
.settings-modal .modal-content {
  width: 90%;
  max-width: 800px;
}

.settings-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: var(--spacing-lg);
}

.settings-tab {
  padding: var(--spacing-sm) var(--spacing-lg);
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  position: relative;
  transition: all var(--transition-base);
  font-size: 0.875rem;
  font-weight: 500;
}

.settings-tab:hover {
  color: var(--text-primary);
}

.settings-tab.active {
  color: var(--accent-color);
}

.settings-tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background-color: var(--accent-color);
}

.settings-section {
  margin-bottom: var(--spacing-xl);
}

.settings-section h3 {
  font-size: 1.125rem;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.settings-group {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.settings-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.settings-row:last-child {
  margin-bottom: 0;
}

.settings-label {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.settings-label .label-text {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.settings-label .label-description {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.settings-control {
  flex: 0 0 auto;
  margin-left: var(--spacing-lg);
}

.settings-input {
  width: 200px;
}

.settings-select {
  width: 200px;
}

.settings-checkbox {
  width: auto;
}

.settings-number {
  width: 100px;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 24px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--bg-surface);
  border: 1px solid var(--border-color);
  transition: all var(--transition-base);
  border-radius: 24px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: all var(--transition-base);
  border-radius: 50%;
}

input:checked + .toggle-slider {
  background-color: var(--accent-color);
  border-color: var(--accent-color);
}

input:checked + .toggle-slider:before {
  transform: translateX(24px);
}

/* Settings Footer */
.settings-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

.settings-info {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.settings-actions {
  display: flex;
  gap: var(--spacing-md);
}
EOF

echo "All CSS files created successfully!"
echo ""
echo "The app should now compile without CSS import errors."
echo "Run 'npm start' to start the application!"