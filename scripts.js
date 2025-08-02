// Initialize Mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    themeVariables: {
        primaryColor: '#8b5cf6',
        primaryTextColor: '#1a1f2e',
        primaryBorderColor: '#2d3548',
        lineColor: '#374151',
        secondaryColor: '#f3f4f6',
        tertiaryColor: '#ffffff',
        background: '#ffffff',
        mainBkg: '#f8fafc',
        secondBkg: '#e2e8f0',
        tertiaryBkg: '#cbd5e1'
    },
    flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
    },
    securityLevel: 'loose'
});

// API Configuration
const API_BASE = (() => {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    const port = '5000';
    
    if (protocol === 'file:' || !hostname) {
        return 'http://localhost:5000/api';
    }
    
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return `http://${hostname}:${port}/api`;
    }
    
    return 'http://localhost:5000/api';
})();

console.log('Using API base:', API_BASE);

// Socket.IO Connection
let socket = null;
let socketConnectionAttempts = 0;
const maxSocketRetries = 3;

const initializeSocket = () => {
    if (socketConnectionAttempts >= maxSocketRetries) {
        console.warn('Max socket connection attempts reached');
        return;
    }

    try {
        const socketUrl = API_BASE.replace('/api', '');
        console.log('Attempting socket connection to:', socketUrl);
        
        socket = io(socketUrl, {
            timeout: 20000,
            reconnection: true,
            reconnectionAttempts: 3,
            reconnectionDelay: 1000,
            forceNew: true,
            transports: ['websocket', 'polling'],
            withCredentials: false
        });

        socket.on('connect', () => {
            console.log('Socket.IO connected successfully');
            socketConnectionAttempts = 0;
            if (window.updateConnectionStatus) {
                window.updateConnectionStatus('connected');
            }
        });

        socket.on('disconnect', (reason) => {
            console.log('Socket.IO disconnected:', reason);
            if (window.updateConnectionStatus) {
                window.updateConnectionStatus('disconnected');
            }
        });

        socket.on('connect_error', (error) => {
            console.warn('Socket.IO connection error:', error.message);
            socketConnectionAttempts++;
            if (window.updateConnectionStatus) {
                window.updateConnectionStatus('error');
            }
        });

    } catch (e) {
        console.error('Socket initialization failed:', e);
        socketConnectionAttempts++;
    }
};

// Initialize socket connection
setTimeout(initializeSocket, 1000);

// API Helper Function
const makeApiRequest = async (endpoint, options = {}) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Network error' }));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Request timed out');
        }
        throw error;
    }
};

// JSON Highlighting
const highlightJSON = (json) => {
    if (typeof json !== 'string') {
        json = JSON.stringify(json, null, 2);
    }
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
        let cls = 'json-number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'json-key';
            } else {
                cls = 'json-string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'json-boolean';
        } else if (/null/.test(match)) {
            cls = 'json-null';
        }
        return `<span class="${cls}">${match}</span>`;
    });
};

// Mermaid Diagram Component
const MermaidDiagram = ({ diagram, title = "Data Flow Diagram" }) => {
    const [isFullscreen, setIsFullscreen] = React.useState(false);
    const [diagramId] = React.useState(`mermaid-${Date.now()}`);
    const diagramRef = React.useRef(null);

    React.useEffect(() => {
        if (diagram && diagramRef.current) {
            renderDiagram();
        }
    }, [diagram]);

    const cleanMermaidDiagram = (rawDiagram) => {
        if (!rawDiagram) return '';
        
        // Clean up common syntax issues
        let cleaned = rawDiagram
            // Fix node shape syntax - remove invalid characters from node names
            .replace(/(\w+)\s*\{\{\s*([^}]+)\s*\}\}/g, '$1["$2"]')
            // Fix database cylinder syntax
            .replace(/(\w+)\s*\[\(\s*([^)]+)\s*\)\]/g, '$1[("$2")]')
            // Fix multi-line labels in arrows - replace newlines with <br/>
            .replace(/\|"([^"]*)\n([^"]*)"/, '|"$1<br/>$2"')
            .replace(/\|"([^"]*)\n([^"]*)\n([^"]*)"/, '|"$1<br/>$2<br/>$3"')
            // Fix long labels that might break syntax
            .replace(/JWT Authenticat/g, 'JWT Auth')
            .replace(/API Key authent/g, 'API Key')
            // Remove comments that might interfere
            .replace(/%%.*$/gm, '')
            // Clean up extra whitespace
            .replace(/\n\s*\n/g, '\n')
            .trim();
        
        return cleaned;
    };

    const createThreatModelingDiagram = (dfdData) => {
        if (!dfdData || !dfdData.dfd) return null;
        
        const dfd = dfdData.dfd;
        let diagram = `graph TB\n`;
        
        // Create trust zones
        const zones = {
            external: [],
            dmz: [],
            application: [],
            data: []
        };
        
        // Clean function to make valid IDs
        const cleanId = (name) => {
            return name.replace(/[^a-zA-Z0-9]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
        };
        
        // Clean function to make safe display names (remove parentheses and special chars)
        const cleanName = (name) => {
            return name.replace(/[()]/g, '').replace(/\s+/g, ' ').trim();
        };
        
        // Categorize entities into zones
        dfd.external_entities?.forEach(entity => {
            const id = cleanId(entity);
            const name = cleanName(entity);
            zones.external.push({ id, name, type: 'entity' });
        });
        
        dfd.processes?.forEach(process => {
            const id = cleanId(process);
            const name = cleanName(process);
            // Determine if it's DMZ or application based on name
            if (process.toLowerCase().includes('gateway') || process.toLowerCase().includes('proxy') || 
                process.toLowerCase().includes('load balancer') || process.toLowerCase().includes('firewall')) {
                zones.dmz.push({ id, name, type: 'process' });
            } else {
                zones.application.push({ id, name, type: 'process' });
            }
        });
        
        dfd.assets?.forEach(asset => {
            const id = cleanId(asset);
            const name = cleanName(asset);
            zones.data.push({ id, name, type: 'asset' });
        });
        
        // Generate subgraphs for each zone
        if (zones.external.length > 0) {
            diagram += `    subgraph External["🌐 External Zone - Untrusted"]\n`;
            zones.external.forEach(item => {
                diagram += `        ${item.id}["👤 ${item.name}"]\n`;
            });
            diagram += `    end\n\n`;
        }
        
        if (zones.dmz.length > 0) {
            diagram += `    subgraph DMZ["🛡️ DMZ Zone - Semi-Trusted"]\n`;
            zones.dmz.forEach(item => {
                diagram += `        ${item.id}["⚙️ ${item.name}"]\n`;
            });
            diagram += `    end\n\n`;
        }
        
        if (zones.application.length > 0) {
            diagram += `    subgraph Application["🏢 Application Zone - Trusted"]\n`;
            zones.application.forEach(item => {
                diagram += `        ${item.id}["⚙️ ${item.name}"]\n`;
            });
            diagram += `    end\n\n`;
        }
        
        if (zones.data.length > 0) {
            diagram += `    subgraph DataZone["💾 Data Zone - Critical Assets"]\n`;
            zones.data.forEach(item => {
                diagram += `        ${item.id}["💾 ${item.name}"]\n`;
            });
            diagram += `    end\n\n`;
        }
        
        // Get all entities for ID mapping
        const allEntities = [
            ...zones.external,
            ...zones.dmz, 
            ...zones.application,
            ...zones.data
        ];
        
        // Create mapping from original names to clean IDs
        const nameToId = {};
        allEntities.forEach(entity => {
            // Try to match based on the original name
            dfd.external_entities?.forEach(orig => {
                if (cleanId(orig) === entity.id) nameToId[orig] = entity.id;
            });
            dfd.processes?.forEach(orig => {
                if (cleanId(orig) === entity.id) nameToId[orig] = entity.id;
            });
            dfd.assets?.forEach(orig => {
                if (cleanId(orig) === entity.id) nameToId[orig] = entity.id;
            });
        });
        
        // Add data flows with security context
        diagram += `    %% Data Flows with Security Analysis\n`;
        dfd.data_flows?.forEach((flow, index) => {
            const sourceId = nameToId[flow.source] || cleanId(flow.source);
            const destId = nameToId[flow.destination] || cleanId(flow.destination);
            
            // Skip if we can't find valid source or destination
            if (!sourceId || !destId) {
                console.warn(`Skipping flow: ${flow.source} -> ${flow.destination} (missing IDs)`);
                return;
            }
            
            // Determine arrow style based on data classification and trust boundary
            let arrowStyle = '-->';
            
            if (flow.data_classification === 'PHI' || flow.data_classification === 'PII' || 
                flow.data_classification === 'PCI' || flow.data_classification?.includes('PHI')) {
                arrowStyle = '==>';
            } else if (flow.data_classification === 'Confidential') {
                arrowStyle = '-->';
            } else {
                arrowStyle = '-.->';
            }
            
            // Create security-focused label (simplified to avoid parsing issues)
            const protocol = (flow.protocol || 'Unknown').replace(/[^\w\s]/g, '');
            const dataClass = (flow.data_classification || 'Public').replace(/[^\w\s]/g, '');
            const auth = (flow.authentication_mechanism || 'None').replace(/[^\w\s]/g, '').substring(0, 15);
            const encrypted = flow.encryption_in_transit ? 'Encrypted' : 'Not Encrypted';
            const trustBoundary = flow.trust_boundary_crossing ? 'Cross TB' : 'Internal';
            
            const label = `${protocol} | ${dataClass} | ${auth} | ${encrypted} | ${trustBoundary}`;
            
            diagram += `    ${sourceId} ${arrowStyle}|"${label}"| ${destId}\n`;
        });
        
        // Add trust boundaries as comments
        diagram += `\n    %% Trust Boundaries:\n`;
        dfd.trust_boundaries?.forEach((boundary, index) => {
            diagram += `    %% ${index + 1}. ${boundary}\n`;
        });
        
        // Add styling for security zones
        diagram += `\n    %% Security Zone Styling\n`;
        diagram += `    classDef external fill:#ff4757,stroke:#ff3742,stroke-width:3px,color:#fff\n`;
        diagram += `    classDef dmz fill:#ffa502,stroke:#ff8c00,stroke-width:2px,color:#000\n`;
        diagram += `    classDef application fill:#3742fa,stroke:#2f40fa,stroke-width:2px,color:#fff\n`;
        diagram += `    classDef data fill:#2ed573,stroke:#20bf6b,stroke-width:2px,color:#000\n`;
        
        // Apply classes
        if (zones.external.length > 0) {
            const externalIds = zones.external.map(item => item.id).join(',');
            diagram += `    class ${externalIds} external\n`;
        }
        if (zones.dmz.length > 0) {
            const dmzIds = zones.dmz.map(item => item.id).join(',');
            diagram += `    class ${dmzIds} dmz\n`;
        }
        if (zones.application.length > 0) {
            const appIds = zones.application.map(item => item.id).join(',');
            diagram += `    class ${appIds} application\n`;
        }
        if (zones.data.length > 0) {
            const dataIds = zones.data.map(item => item.id).join(',');
            diagram += `    class ${dataIds} data\n`;
        }
        
        // Add legend as comments
        diagram += `\n    %% THREAT MODELING LEGEND:\n`;
        diagram += `    %% Red External Zone: Untrusted - highest attack surface\n`;
        diagram += `    %% Orange DMZ Zone: Semi-trusted - exposed but protected\n`;
        diagram += `    %% Blue Application Zone: Trusted - business logic\n`;
        diagram += `    %% Green Data Zone: Critical assets - maximum protection\n`;
        diagram += `    %% Thick arrows: High-risk data PHI/PII/PCI\n`;
        diagram += `    %% Normal arrows: Medium-risk Confidential data\n`;
        diagram += `    %% Dotted arrows: Low-risk Public/Internal data\n`;
        
        return diagram;
    };

    const renderDiagram = async () => {
        if (!diagram || !diagramRef.current) return;

        try {
            // Clear previous content
            diagramRef.current.innerHTML = '';
            
            // Try to create a comprehensive threat modeling diagram first
            let diagramToRender = diagram;
            
            // If we have DFD data, create a better threat modeling diagram
            if (typeof window.currentDfdData !== 'undefined' && window.currentDfdData) {
                const threatModelingDiagram = createThreatModelingDiagram(window.currentDfdData);
                if (threatModelingDiagram) {
                    diagramToRender = threatModelingDiagram;
                }
            }
            
            // Clean the diagram syntax
            const cleanedDiagram = cleanMermaidDiagram(diagramToRender);
            console.log('Rendering threat modeling diagram:', cleanedDiagram);
            
            // Validate and render the diagram
            const { svg } = await mermaid.render(diagramId, cleanedDiagram);
            diagramRef.current.innerHTML = svg;
            
            // Add zoom and pan functionality
            const svgElement = diagramRef.current.querySelector('svg');
            if (svgElement) {
                svgElement.style.maxWidth = '100%';
                svgElement.style.height = 'auto';
                svgElement.style.cursor = 'grab';
                
                // Add click to zoom functionality
                svgElement.addEventListener('click', () => {
                    if (!isFullscreen) {
                        setIsFullscreen(true);
                    }
                });
            }
        } catch (error) {
            console.error('Mermaid render error:', error);
            
            // Try fallback with simpler syntax
            try {
                const fallbackDiagram = createFallbackDiagram(diagram);
                const { svg } = await mermaid.render(diagramId + '_fallback', fallbackDiagram);
                diagramRef.current.innerHTML = svg;
            } catch (fallbackError) {
                console.error('Fallback diagram also failed:', fallbackError);
                diagramRef.current.innerHTML = `
                    <div style="color: #ef4444; padding: 40px; text-align: center;">
                        <h3>⚠️ Diagram Render Error</h3>
                        <p>Unable to render the Mermaid diagram. The syntax may be incompatible with this version.</p>
                        <details style="margin-top: 20px; text-align: left;">
                            <summary style="cursor: pointer;">Show Raw Diagram Code</summary>
                            <pre style="background: #f5f5f5; padding: 15px; border-radius: 6px; margin-top: 10px; font-size: 0.85em; color: #333; overflow: auto; max-height: 300px;">${diagram}</pre>
                        </details>
                        <div style="margin-top: 20px;">
                            <button onclick="this.parentElement.parentElement.innerHTML='<p>Diagram hidden. Please check backend logs for Mermaid syntax details.</p>'" 
                                    style="background: #8b5cf6; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">
                                Hide Diagram
                            </button>
                        </div>
                    </div>
                `;
            }
        }
    };

    const createFallbackDiagram = (originalDiagram) => {
        // Create a simplified fallback diagram
        return `
graph TD
    A[External Entities] --> B[DMZ Services]
    B --> C[Application Layer]
    C --> D[Data Layer]
    
    classDef external fill:#ff4757,stroke:#ff3742,stroke-width:2px,color:#fff
    classDef dmz fill:#ffa502,stroke:#ff8c00,stroke-width:2px,color:#000
    classDef application fill:#3742fa,stroke:#2f40fa,stroke-width:2px,color:#fff
    classDef data fill:#2ed573,stroke:#20bf6b,stroke-width:2px,color:#000
    
    class A external
    class B dmz
    class C application
    class D data
    
    A -.->|"HTTPS"| B
    B -.->|"Encrypted"| C
    C -.->|"Secure"| D
                `.trim();
    };

    const downloadSVG = () => {
        const svgElement = diagramRef.current?.querySelector('svg');
        if (svgElement) {
            const svgData = new XMLSerializer().serializeToString(svgElement);
            const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
            const svgUrl = URL.createObjectURL(svgBlob);
            
            const downloadLink = document.createElement('a');
            downloadLink.href = svgUrl;
            downloadLink.download = 'threat-model-dfd.svg';
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            URL.revokeObjectURL(svgUrl);
        }
    };

    const downloadPNG = async () => {
        const svgElement = diagramRef.current?.querySelector('svg');
        if (svgElement) {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            const svgData = new XMLSerializer().serializeToString(svgElement);
            const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
            const url = URL.createObjectURL(svgBlob);
            
            img.onload = () => {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0);
                
                canvas.toBlob((blob) => {
                    const downloadLink = document.createElement('a');
                    downloadLink.href = URL.createObjectURL(blob);
                    downloadLink.download = 'threat-model-dfd.png';
                    document.body.appendChild(downloadLink);
                    downloadLink.click();
                    document.body.removeChild(downloadLink);
                    URL.revokeObjectURL(downloadLink.href);
                });
                URL.revokeObjectURL(url);
            };
            
            img.src = url;
        }
    };

    if (!diagram) {
        return (
            <div className="mermaid-viewer">
                <div style={{ color: '#9ca3af', padding: '40px' }}>
                    <h3>📊 No Diagram Available</h3>
                    <p>The Mermaid diagram will appear here once generated.</p>
                </div>
            </div>
        );
    }

    return (
        <>
            <div className="mermaid-viewer">
                <div className="mermaid-toolbar">
                    <button className="mermaid-btn" onClick={() => setIsFullscreen(true)} title="View Fullscreen">
                        🔍 Fullscreen
                    </button>
                    <button className="mermaid-btn" onClick={downloadSVG} title="Download as SVG">
                        📥 SVG
                    </button>
                    <button className="mermaid-btn" onClick={downloadPNG} title="Download as PNG">
                        📥 PNG
                    </button>
                </div>
                <div className="mermaid-container">
                    <div ref={diagramRef} style={{ width: '100%', height: '100%' }}></div>
                </div>
            </div>

            {isFullscreen && (
                <div className="mermaid-fullscreen" onClick={() => setIsFullscreen(false)}>
                    <div style={{ position: 'relative', maxWidth: '95%', maxHeight: '95%', overflow: 'auto' }}>
                        <button 
                            style={{
                                position: 'absolute',
                                top: '10px',
                                right: '10px',
                                background: 'rgba(0,0,0,0.7)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '50%',
                                width: '40px',
                                height: '40px',
                                cursor: 'pointer',
                                fontSize: '20px',
                                zIndex: 10
                            }}
                            onClick={(e) => {
                                e.stopPropagation();
                                setIsFullscreen(false);
                            }}
                        >
                            ×
                        </button>
                        <div dangerouslySetInnerHTML={{ __html: diagramRef.current?.innerHTML || '' }} />
                    </div>
                </div>
            )}
        </>
    );
};

// Edit Modal Components
const EditModal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;

    return (
        <div className="edit-modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="edit-modal">
                <h3>{title}</h3>
                {children}
            </div>
        </div>
    );
};

const EditableComponentList = ({ 
    title, 
    items, 
    onEdit, 
    onDelete, 
    onAdd, 
    type,
    metadata = {} 
}) => {
    const [showAddForm, setShowAddForm] = React.useState(false);
    const [newItem, setNewItem] = React.useState('');

    const handleAdd = () => {
        if (newItem.trim()) {
            onAdd(newItem.trim());
            setNewItem('');
            setShowAddForm(false);
        }
    };

    const getCriticalityIndicator = (item) => {
        const itemMetadata = metadata[item];
        if (!itemMetadata?.criticality) return null;
        
        const criticality = itemMetadata.criticality.toLowerCase();
        return (
            <span className={`criticality-indicator criticality-${criticality}`}>
                {itemMetadata.criticality}
            </span>
        );
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <h4 style={{ color: '#8b5cf6', margin: 0 }}>{title} ({items?.length || 0})</h4>
                <button 
                    className="btn btn-sm btn-primary"
                    onClick={() => setShowAddForm(true)}
                >
                    ➕ Add {type}
                </button>
            </div>
            
            <div className="editable-list">
                {items?.map((item, index) => (
                    <div key={index} className="editable-item">
                        <div style={{ flex: 1 }}>
                            <span>{item}</span>
                            {getCriticalityIndicator(item)}
                        </div>
                        <div className="item-actions">
                            <button 
                                className="btn btn-icon btn-secondary"
                                onClick={() => onEdit(item, index)}
                                title="Edit"
                            >
                                ✏️
                            </button>
                            <button 
                                className="btn btn-icon btn-danger"
                                onClick={() => onDelete(index)}
                                title="Delete"
                            >
                                🗑️
                            </button>
                        </div>
                    </div>
                )) || (
                    <div className="editable-item">
                        <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>No {type}s defined</span>
                    </div>
                )}
            </div>

            {showAddForm && (
                <div className="add-item-form">
                    <div className="form-group">
                        <label>New {type}:</label>
                        <input
                            type="text"
                            className="form-input"
                            value={newItem}
                            onChange={(e) => setNewItem(e.target.value)}
                            placeholder={`Enter ${type} name...`}
                            onKeyPress={(e) => e.key === 'Enter' && handleAdd()}
                            autoFocus
                        />
                    </div>
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <button className="btn btn-sm btn-success" onClick={handleAdd}>
                            ✅ Add
                        </button>
                        <button 
                            className="btn btn-sm btn-secondary" 
                            onClick={() => {
                                setShowAddForm(false);
                                setNewItem('');
                            }}
                        >
                            ❌ Cancel
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

const DataFlowEditor = ({ flow, onSave, onCancel }) => {
    const [editedFlow, setEditedFlow] = React.useState({ ...flow });

    const handleSave = () => {
        onSave(editedFlow);
    };

    return (
        <div>
            <div className="form-group">
                <label>Source:</label>
                <input
                    type="text"
                    className="form-input"
                    value={editedFlow.source || ''}
                    onChange={(e) => setEditedFlow({ ...editedFlow, source: e.target.value })}
                />
            </div>
            
            <div className="form-group">
                <label>Destination:</label>
                <input
                    type="text"
                    className="form-input"
                    value={editedFlow.destination || ''}
                    onChange={(e) => setEditedFlow({ ...editedFlow, destination: e.target.value })}
                />
            </div>

            <div className="form-group">
                <label>Data Description:</label>
                <textarea
                    className="form-textarea"
                    value={editedFlow.data_description || ''}
                    onChange={(e) => setEditedFlow({ ...editedFlow, data_description: e.target.value })}
                    rows={3}
                />
            </div>

            <div className="form-group">
                <label>Data Classification:</label>
                <select
                    className="form-select"
                    value={editedFlow.data_classification || 'Public'}
                    onChange={(e) => setEditedFlow({ ...editedFlow, data_classification: e.target.value })}
                >
                    <option value="Public">Public</option>
                    <option value="Internal">Internal</option>
                    <option value="Confidential">Confidential</option>
                    <option value="PII">PII (Personally Identifiable Information)</option>
                    <option value="PHI">PHI (Protected Health Information)</option>
                    <option value="PCI">PCI (Payment Card Industry)</option>
                </select>
            </div>

            <div className="form-group">
                <label>Protocol:</label>
                <select
                    className="form-select"
                    value={editedFlow.protocol || 'HTTPS'}
                    onChange={(e) => setEditedFlow({ ...editedFlow, protocol: e.target.value })}
                >
                    <option value="HTTPS">HTTPS</option>
                    <option value="HTTP">HTTP</option>
                    <option value="TLS">TLS</option>
                    <option value="TCP">TCP</option>
                    <option value="UDP">UDP</option>
                    <option value="JDBC">JDBC</option>
                    <option value="API">API</option>
                    <option value="Message Queue">Message Queue</option>
                    <option value="Unknown">Unknown</option>
                </select>
            </div>

            <div className="form-group">
                <label>Authentication Mechanism:</label>
                <select
                    className="form-select"
                    value={editedFlow.authentication_mechanism || 'None'}
                    onChange={(e) => setEditedFlow({ ...editedFlow, authentication_mechanism: e.target.value })}
                >
                    <option value="None">None</option>
                    <option value="JWT">JWT Token</option>
                    <option value="OAuth 2.0">OAuth 2.0</option>
                    <option value="SAML SSO">SAML SSO</option>
                    <option value="API Key">API Key</option>
                    <option value="mTLS">Mutual TLS</option>
                    <option value="Smart Card Auth">Smart Card Authentication</option>
                    <option value="MFA">Multi-Factor Authentication</option>
                    <option value="Database Credentials">Database Credentials</option>
                    <option value="Service Account">Service Account</option>
                </select>
            </div>

            <div className="form-group">
                <div className="checkbox-group">
                    <input
                        type="checkbox"
                        checked={editedFlow.encryption_in_transit || false}
                        onChange={(e) => setEditedFlow({ ...editedFlow, encryption_in_transit: e.target.checked })}
                    />
                    <label>Encryption in Transit</label>
                </div>
                <div className="checkbox-group">
                    <input
                        type="checkbox"
                        checked={editedFlow.trust_boundary_crossing || false}
                        onChange={(e) => setEditedFlow({ ...editedFlow, trust_boundary_crossing: e.target.checked })}
                    />
                    <label>Crosses Trust Boundary</label>
                </div>
            </div>

            <div className="form-actions">
                <button className="btn btn-success" onClick={handleSave}>
                    💾 Save Changes
                </button>
                <button className="btn btn-secondary" onClick={onCancel}>
                    ❌ Cancel
                </button>
            </div>
        </div>
    );
};

const AssetMetadataEditor = ({ asset, metadata, onSave, onCancel }) => {
    const [editedMetadata, setEditedMetadata] = React.useState({
        criticality: metadata?.criticality || 'Medium',
        exposure: metadata?.exposure || 'Internal',
        data_classification: metadata?.data_classification || ['Internal'],
        ...metadata
    });

    const handleSave = () => {
        onSave(asset, editedMetadata);
    };

    return (
        <div>
            <div className="form-group">
                <label>Asset Name:</label>
                <input
                    type="text"
                    className="form-input"
                    value={asset}
                    disabled
                    style={{ opacity: 0.7 }}
                />
                <small style={{ color: '#9ca3af' }}>Asset name cannot be changed here</small>
            </div>

            <div className="form-group">
                <label>Criticality Level:</label>
                <select
                    className="form-select"
                    value={editedMetadata.criticality}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata, criticality: e.target.value })}
                >
                    <option value="Critical">Critical - System failure causes major business impact</option>
                    <option value="High">High - Important for business operations</option>
                    <option value="Medium">Medium - Standard business importance</option>
                    <option value="Low">Low - Minimal business impact</option>
                </select>
            </div>

            <div className="form-group">
                <label>Exposure Level:</label>
                <select
                    className="form-select"
                    value={editedMetadata.exposure}
                    onChange={(e) => setEditedMetadata({ ...editedMetadata, exposure: e.target.value })}
                >
                    <option value="Internet-facing">Internet-facing - Directly accessible from internet</option>
                    <option value="DMZ">DMZ - In demilitarized zone, limited exposure</option>
                    <option value="Internal">Internal - Only accessible from internal network</option>
                    <option value="Isolated">Isolated - Air-gapped or highly restricted</option>
                </select>
            </div>

            <div className="form-group">
                <label>Data Types Stored:</label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginTop: '10px' }}>
                    {['PII', 'PHI', 'PCI', 'Confidential', 'Internal', 'Public'].map(type => (
                        <div key={type} className="checkbox-group">
                            <input
                                type="checkbox"
                                checked={editedMetadata.data_classification?.includes(type) || false}
                                onChange={(e) => {
                                    const current = editedMetadata.data_classification || [];
                                    if (e.target.checked) {
                                        setEditedMetadata({
                                            ...editedMetadata,
                                            data_classification: [...current, type]
                                        });
                                    } else {
                                        setEditedMetadata({
                                            ...editedMetadata,
                                            data_classification: current.filter(t => t !== type)
                                        });
                                    }
                                }}
                            />
                            <label>{type}</label>
                        </div>
                    ))}
                </div>
            </div>

            <div className="form-actions">
                <button className="btn btn-success" onClick={handleSave}>
                    💾 Save Metadata
                </button>
                <button className="btn btn-secondary" onClick={onCancel}>
                    ❌ Cancel
                </button>
            </div>
        </div>
    );
};
const Notification = ({ type, message, onClose }) => {
    React.useEffect(() => {
        const timer = setTimeout(onClose, 5000);
        return () => clearTimeout(timer);
    }, []);

    return (
        <div className={`alert alert-${type}`} style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: 1001,
            boxShadow: '0 5px 20px rgba(0, 0, 0, 0.3)',
            animation: 'slideIn 0.3s ease-out'
        }}>
            <span>{type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️'}</span>
            <span>{message}</span>
        </div>
    );
};

// Connection Status Component
const ConnectionStatus = ({ status }) => {
    const getStatusInfo = () => {
        switch (status) {
            case 'connected':
                return { text: 'Connected', class: 'connected', icon: '🟢' };
            case 'disconnected':
                return { text: 'Disconnected', class: 'disconnected', icon: '🔴' };
            case 'connecting':
                return { text: 'Connecting...', class: 'connecting', icon: '🟡' };
            case 'error':
                return { text: 'Connection Error', class: 'disconnected', icon: '🔴' };
            default:
                return { text: 'Unknown', class: 'disconnected', icon: '⚪' };
        }
    };

    const { text, class: className, icon } = getStatusInfo();

    return (
        <div className={`connection-status ${className}`}>
            <span>{icon}</span>
            <span>WebSocket: {text}</span>
        </div>
    );
};

// File Upload Component
const FileUploadComponent = ({ onUpload, loading }) => (
    <div className="card">
        <div className="card-header">
            <h2>📄 Upload Document</h2>
            <span className="tag tag-info">Step 1</span>
        </div>
        <div 
            style={{
                border: '3px dashed #2d3548',
                borderRadius: '12px',
                padding: '60px',
                textAlign: 'center',
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'all 0.3s ease',
                background: 'rgba(139, 92, 246, 0.02)',
                opacity: loading ? 0.6 : 1
            }}
            onClick={() => !loading && document.getElementById('fileInput').click()}
            onDragOver={(e) => {
                if (loading) return;
                e.preventDefault();
                e.currentTarget.style.borderColor = '#8b5cf6';
                e.currentTarget.style.background = 'rgba(139, 92, 246, 0.05)';
            }}
            onDragLeave={(e) => {
                e.currentTarget.style.borderColor = '#2d3548';
                e.currentTarget.style.background = 'rgba(139, 92, 246, 0.02)';
            }}
            onDrop={(e) => {
                if (loading) return;
                e.preventDefault();
                e.currentTarget.style.borderColor = '#2d3548';
                e.currentTarget.style.background = 'rgba(139, 92, 246, 0.02)';
                const files = Array.from(e.dataTransfer.files);
                if (files.length > 0) onUpload(files);
            }}
        >
            <input 
                type="file" 
                id="fileInput" 
                style={{display: 'none'}}
                onChange={(e) => onUpload(Array.from(e.target.files))}
                accept=".txt,.pdf,.doc,.docx"
                disabled={loading}
            />
            <div style={{fontSize: '4em', marginBottom: '20px', color: '#8b5cf6'}}>
                {loading ? '⏳' : '📁'}
            </div>
            <div style={{fontSize: '1.2em', marginBottom: '10px', fontWeight: '600'}}>
                {loading ? 'Processing...' : 'Drop files here or click to browse'}
            </div>
            <div style={{fontSize: '0.95em', color: '#9ca3af', marginBottom: '20px'}}>
                Supports TXT, PDF, DOC, DOCX files
            </div>
            <div style={{fontSize: '0.85em', color: '#6b7280'}}>
                Maximum file size: 50MB
            </div>
        </div>
    </div>
);

// Step Content Display Component
const StepContentDisplay = ({ step, stepIndex, currentStep, pipelineState, runStep, loading, onUpload }) => {
    const [activeTab, setActiveTab] = React.useState('overview');

    if (stepIndex !== currentStep) return null;

    const renderStepContent = () => {
        switch (stepIndex) {
            case 0: // Upload
                if (step.status === 'pending') {
                    return <FileUploadComponent onUpload={onUpload} loading={loading} />;
                } else if (step.status === 'completed' && step.data) {
                    return (
                        <div className="card">
                            <div className="card-header">
                                <h2>📄 Document Upload Complete</h2>
                                <span className="tag tag-success">Completed</span>
                            </div>
                            <div className="data-grid">
                                <div className="metric-card">
                                    <div className="metric-value" style={{color: '#10b981'}}>
                                        {step.data.text_length?.toLocaleString() || 0}
                                    </div>
                                    <div className="metric-label">Characters</div>
                                </div>
                                <div className="metric-card">
                                    <div className="metric-value" style={{color: '#8b5cf6'}}>
                                        {step.data.filename || 'Unknown'}
                                    </div>
                                    <div className="metric-label">File Name</div>
                                </div>
                            </div>
                            {step.data.text_preview && (
                                <div style={{marginTop: '20px'}}>
                                    <h3>Document Preview:</h3>
                                    <div className="json-viewer" style={{maxHeight: '200px'}}>
                                        <pre>{step.data.text_preview}</pre>
                                    </div>
                                </div>
                            )}
                            <div style={{marginTop: '20px'}}>
                                <button 
                                    className="btn btn-primary"
                                    onClick={() => runStep(1, false)}
                                    disabled={loading}
                                >
                                    {loading ? '⏳ Running...' : '▶️ Extract DFD Components'}
                                </button>
                            </div>
                        </div>
                    );
                }
                break;

            case 1: // DFD with Mermaid Diagram and Edit Functionality
                if (step.status === 'completed' && step.data) {
                    const dfd = step.data.dfd || {};
                    const mermaidDiagram = step.data.mermaid || null;
                    
                    return (
                        <DFDStepContent 
                            stepData={step.data}
                            dfd={dfd}
                            mermaidDiagram={mermaidDiagram}
                            onUpdate={(updatedData) => {
                                updateStepStatus(1, 'completed', updatedData);
                                showNotification('DFD updated successfully!', 'success');
                            }}
                            runStep={runStep}
                            setCurrentStep={setCurrentStep}
                            loading={loading}
                        />
                    );
                }
                break;

            case 2: // Threats with Edit Functionality
            case 3: // Refined Threats with Edit Functionality
                if (step.status === 'completed' && step.data) {
                    const threats = step.data.threats || [];
                    
                    return (
                        <ThreatStepContent 
                            stepData={step.data}
                            threats={threats}
                            stepIndex={stepIndex}
                            onUpdate={(updatedData) => {
                                updateStepStatus(stepIndex, 'completed', updatedData);
                                showNotification(`${step.name} updated successfully!`, 'success');
                            }}
                            runStep={runStep}
                            setCurrentStep={setCurrentStep}
                            loading={loading}
                        />
                    );
                }
                break;

            case 4: // Attack Paths
                if (step.status === 'completed' && step.data) {
                    const attackPaths = step.data.attack_paths || [];
                    return (
                        <div className="step-content">
                            <div className="card">
                                <div className="card-header">
                                    <h2>🎯 Attack Path Analysis Complete</h2>
                                    <span className="tag tag-success">Completed</span>
                                </div>
                                <div className="data-grid">
                                    <div className="metric-card">
                                        <div className="metric-value" style={{color: '#8b5cf6'}}>
                                            {attackPaths.length}
                                        </div>
                                        <div className="metric-label">Attack Paths</div>
                                    </div>
                                    <div className="metric-card">
                                        <div className="metric-value" style={{color: '#ef4444'}}>
                                            {attackPaths.filter(p => p.path_feasibility === 'Highly Likely').length}
                                        </div>
                                        <div className="metric-label">High Feasibility</div>
                                    </div>
                                    <div className="metric-card">
                                        <div className="metric-value" style={{color: '#f59e0b'}}>
                                            {attackPaths.filter(p => p.combined_impact === 'Critical').length}
                                        </div>
                                        <div className="metric-label">Critical Impact</div>
                                    </div>
                                    <div className="metric-card">
                                        <div className="metric-value" style={{color: '#10b981'}}>
                                            {step.data.defense_priorities?.length || 0}
                                        </div>
                                        <div className="metric-label">Defense Priorities</div>
                                    </div>
                                </div>

                                <div className="alert alert-success">
                                    <span>🎉</span>
                                    <span><strong>Threat Modeling Complete!</strong> Your security analysis is ready for review.</span>
                                </div>

                                <div className="tabs">
                                    <button 
                                        className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
                                        onClick={() => setActiveTab('overview')}
                                    >
                                        📊 Overview
                                    </button>
                                    <button 
                                        className={`tab ${activeTab === 'paths' ? 'active' : ''}`}
                                        onClick={() => setActiveTab('paths')}
                                    >
                                        🎯 Attack Paths
                                    </button>
                                    <button 
                                        className={`tab ${activeTab === 'data' ? 'active' : ''}`}
                                        onClick={() => setActiveTab('data')}
                                    >
                                        📋 Raw Data
                                    </button>
                                </div>

                                {activeTab === 'overview' && (
                                    <div>
                                        <h3 style={{marginBottom: '15px'}}>🛡️ Defense Priorities</h3>
                                        <div style={{maxHeight: '300px', overflowY: 'auto'}}>
                                            {(step.data.defense_priorities || []).slice(0, 5).map((priority, index) => (
                                                <div key={index} style={{
                                                    padding: '15px',
                                                    margin: '10px 0',
                                                    background: '#0a0e1a',
                                                    borderRadius: '8px',
                                                    borderLeft: `4px solid ${
                                                        priority.priority === 'Critical' ? '#ef4444' :
                                                        priority.priority === 'High' ? '#f59e0b' : '#10b981'
                                                    }`
                                                }}>
                                                    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px'}}>
                                                        <strong>{priority.recommendation}</strong>
                                                        <span className={`tag ${
                                                            priority.priority === 'Critical' ? 'tag-danger' :
                                                            priority.priority === 'High' ? 'tag-warning' : 'tag-success'
                                                        }`}>
                                                            {priority.priority}
                                                        </span>
                                                    </div>
                                                    <p style={{fontSize: '0.9em', color: '#d1d5db', marginBottom: '8px'}}>
                                                        {priority.impact}
                                                    </p>
                                                    <p style={{fontSize: '0.85em', color: '#9ca3af'}}>
                                                        <strong>Effort:</strong> {priority.effort} | 
                                                        <strong> Category:</strong> {priority.category}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {activeTab === 'paths' && (
                                    <div style={{maxHeight: '500px', overflowY: 'auto'}}>
                                        {attackPaths.map((path, index) => (
                                            <div key={index} style={{
                                                padding: '15px',
                                                margin: '10px 0',
                                                background: '#0a0e1a',
                                                borderRadius: '8px',
                                                borderLeft: `4px solid ${
                                                    path.path_feasibility === 'Highly Likely' ? '#ef4444' :
                                                    path.path_feasibility === 'Realistic' ? '#f59e0b' : '#10b981'
                                                }`
                                            }}>
                                                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px'}}>
                                                    <strong>{path.scenario_name}</strong>
                                                    <span className={`tag ${
                                                        path.path_feasibility === 'Highly Likely' ? 'tag-danger' :
                                                        path.path_feasibility === 'Realistic' ? 'tag-warning' : 'tag-success'
                                                    }`}>
                                                        {path.path_feasibility}
                                                    </span>
                                                </div>
                                                <p style={{fontSize: '0.9em', color: '#d1d5db', marginBottom: '8px'}}>
                                                    <strong>Path:</strong> {path.entry_point} → {path.target_asset} ({path.total_steps} steps)
                                                </p>
                                                <p style={{fontSize: '0.85em', color: '#9ca3af'}}>
                                                    <strong>Impact:</strong> {path.combined_impact} | 
                                                    <strong> Likelihood:</strong> {path.combined_likelihood} |
                                                    <strong> Time:</strong> {path.time_to_compromise}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {activeTab === 'data' && (
                                    <div className="json-viewer" style={{maxHeight: '500px'}}>
                                        <pre dangerouslySetInnerHTML={{__html: highlightJSON(step.data)}} />
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                }
                break;
        }

        // Default content for pending steps
        if (step.status === 'pending') {
            return (
                <div className="card">
                    <div className="card-header">
                        <h2>{step.name}</h2>
                        <span className="tag tag-info">Ready</span>
                    </div>
                    <p style={{marginBottom: '20px'}}>
                        Step {stepIndex + 1} of the threat modeling pipeline. 
                        {stepIndex > 0 && pipelineState.steps[stepIndex - 1].status !== 'completed' && 
                            ' Complete the previous step first.'}
                    </p>
                    <button 
                        className="btn btn-primary"
                        onClick={() => runStep(stepIndex, false)}
                        disabled={loading || (stepIndex > 0 && pipelineState.steps[stepIndex - 1].status !== 'completed')}
                    >
                        {loading ? '⏳ Running...' : `▶️ Run ${step.name}`}
                    </button>
                </div>
            );
        }

        // Default content for error state
        if (step.status === 'error') {
            return (
                <div className="card">
                    <div className="card-header">
                        <h2>{step.name}</h2>
                        <span className="tag tag-danger">Error</span>
                    </div>
                    <div className="alert alert-error">
                        <span>⚠️</span>
                        <span>This step encountered an error. Check the logs for details.</span>
                    </div>
                    <button 
                        className="btn btn-primary"
                        onClick={() => runStep(stepIndex, false)}
                        disabled={loading}
                    >
                        {loading ? '⏳ Retrying...' : '🔄 Retry Step'}
                    </button>
                </div>
            );
        }

        return (
            <div className="card">
                <h2>{step.name}</h2>
                <p>No content available for this step.</p>
            </div>
        );
    };

    return (
        <div className="step-content">
            {renderStepContent()}
        </div>
    );
};

// Main App Component
const ThreatModelingApp = () => {
    const [currentStep, setCurrentStep] = React.useState(0);
    const [pipelineState, setPipelineState] = React.useState({
        steps: [
            { id: 1, name: 'Upload Document', status: 'pending', data: null },
            { id: 2, name: 'Extract DFD', status: 'pending', data: null },
            { id: 3, name: 'Generate Threats', status: 'pending', data: null },
            { id: 4, name: 'Refine Threats', status: 'pending', data: null },
            { id: 5, name: 'Analyze Attack Paths', status: 'pending', data: null }
        ],
        logs: []
    });
    const [loading, setLoading] = React.useState(false);
    const [currentOperation, setCurrentOperation] = React.useState('');
    const [notification, setNotification] = React.useState(null);
    const [socketStatus, setSocketStatus] = React.useState('connecting');
    const [backendStatus, setBackendStatus] = React.useState('unknown');

    // Set global connection status updater
    React.useEffect(() => {
        window.updateConnectionStatus = setSocketStatus;
        return () => {
            window.updateConnectionStatus = null;
        };
    }, []);

    // Check backend connectivity on mount
    React.useEffect(() => {
        checkBackendHealth();
    }, []);

    const showNotification = (message, type = 'info') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 5000);
    };

    const checkBackendHealth = async () => {
        try {
            console.log('Checking backend health...');
            const data = await makeApiRequest('/health');
            console.log('Backend health check:', data);
            setBackendStatus('healthy');
        } catch (error) {
            console.error('Backend health check failed:', error);
            setBackendStatus('error');
            showNotification(`Backend connection failed: ${error.message}`, 'error');
        }
    };

    const handleFileUpload = async (files) => {
        if (!files || files.length === 0) return;

        console.log('Starting file upload...', files[0]?.name);
        
        const formData = new FormData();
        formData.append('document', files[0]);

        setLoading(true);
        setCurrentOperation('Uploading and extracting text from document...');
        updateStepStatus(0, 'running');
        
        try {
            console.log('Sending request to:', `${API_BASE}/upload`);
            
            const response = await fetch(`${API_BASE}/upload`, {
                method: 'POST',
                body: formData
            });
            
            console.log('Response status:', response.status);
            
            const data = await response.json();
            console.log('Response data:', data);
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            updateStepStatus(0, 'completed', data);
            setLoading(false);
            setCurrentOperation('');
            showNotification('Document uploaded successfully!', 'success');
            
        } catch (error) {
            console.error('Upload error details:', error);
            updateStepStatus(0, 'error');
            setLoading(false);
            setCurrentOperation('');
            showNotification(`Upload failed: ${error.message}`, 'error');
        }
    };

    const runStep = async (stepIndex, skipReview = false) => {
        const step = pipelineState.steps[stepIndex];
        setLoading(true);
        updateStepStatus(stepIndex, 'running');
        
        const stepDescriptions = {
            1: 'Extracting DFD components from document...',
            2: 'Generating threats using STRIDE methodology...',
            3: 'Refining threats and removing duplicates...',
            4: 'Analyzing attack paths and scenarios...'
        };
        
        setCurrentOperation(stepDescriptions[stepIndex] || `Running ${step.name}...`);

        try {
            const response = await fetch(`${API_BASE}/run-step`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    step: step.id,
                    input: stepIndex > 0 ? pipelineState.steps[stepIndex - 1]?.data : {}
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Step failed');
            }
            
            updateStepStatus(stepIndex, 'completed', data);
            setLoading(false);
            setCurrentOperation('');
            showNotification(`${step.name} completed successfully!`, 'success');
            
        } catch (error) {
            updateStepStatus(stepIndex, 'error');
            setLoading(false);
            setCurrentOperation('');
            showNotification(`Step failed: ${error.message}`, 'error');
        }
    };

    const updateStepStatus = (index, status, data = null) => {
        setPipelineState(prev => {
            const newSteps = [...prev.steps];
            newSteps[index] = { ...newSteps[index], status, data };
            return { ...prev, steps: newSteps };
        });
    };

    const resetPipeline = () => {
        if (loading) {
            showNotification('Cannot reset while a step is running', 'warning');
            return;
        }
        
        setPipelineState(prev => ({
            ...prev,
            steps: prev.steps.map(step => ({ ...step, status: 'pending', data: null }))
        }));
        setCurrentStep(0);
        showNotification('Pipeline reset successfully', 'success');
    };

    // Simple components for this demo
    const PipelineStep = ({ step, index, active, onClick }) => {
        const icons = ['📄', '🔗', '⚠️', '✨', '🎯'];
        
        return (
            <div 
                className={`pipeline-step ${active ? 'active' : ''} ${step.status}`}
                onClick={onClick}
            >
                <div className="step-title">
                    <span style={{fontSize: '1.2em'}}>{icons[index]}</span>
                    {step.name}
                    {step.status === 'running' && (
                        <span className="loading-spinner" style={{width: '16px', height: '16px'}} />
                    )}
                </div>
                <div style={{fontSize: '0.85em', color: '#9ca3af'}}>
                    {step.status === 'completed' && `✓ Completed`}
                    {step.status === 'error' && 'Failed - Click to retry'}
                    {step.status === 'pending' && 'Ready to run'}
                    {step.status === 'running' && 'Processing...'}
                </div>
            </div>
        );
    };

    return (
        <div className="app-container">
            {notification && (
                <Notification 
                    type={notification.type}
                    message={notification.message}
                    onClose={() => setNotification(null)}
                />
            )}

            {/* Sidebar */}
            <div className="sidebar">
                <div className="sidebar-header">
                    <h1>🛡️ Threat Modeling</h1>
                    <p style={{fontSize: '0.95em', color: '#9ca3af'}}>
                        Advanced Security Analysis Pipeline
                    </p>
                </div>
                
                {/* Connection Status */}
                <ConnectionStatus status={socketStatus} />
                
                <div className={`connection-status ${backendStatus === 'healthy' ? 'connected' : 'disconnected'}`}>
                    <span>{backendStatus === 'healthy' ? '🟢' : '🔴'}</span>
                    <span>Backend: {backendStatus === 'healthy' ? 'Online' : 'Offline'}</span>
                </div>
                
                {/* Pipeline Steps */}
                {pipelineState.steps.map((step, index) => (
                    <PipelineStep
                        key={step.id}
                        step={step}
                        index={index}
                        active={currentStep === index}
                        onClick={() => setCurrentStep(index)}
                    />
                ))}
                
                {/* Controls */}
                <div style={{padding: '25px', marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '15px'}}>
                    <button 
                        className="btn btn-secondary" 
                        style={{width: '100%'}}
                        onClick={resetPipeline}
                        disabled={loading}
                    >
                        🔄 Reset Pipeline
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className="main-content">
                <div className="topbar">
                    <div className="tabs">
                        <button className="tab active">
                            📊 Pipeline
                        </button>
                    </div>
                    
                    <div style={{display: 'flex', alignItems: 'center', gap: '15px'}}>
                        <div style={{fontSize: '0.9em', color: '#9ca3af'}}>
                            Step {currentStep + 1} of {pipelineState.steps.length}
                        </div>
                    </div>
                </div>

                <div className="content-area">
                    <StepContentDisplay
                        step={pipelineState.steps[currentStep]}
                        stepIndex={currentStep}
                        currentStep={currentStep}
                        pipelineState={pipelineState}
                        runStep={runStep}
                        loading={loading}
                        onUpload={handleFileUpload}
                    />
                </div>
            </div>

            {loading && (
                <div className="loading-overlay">
                    <div style={{
                        background: '#1a1f2e',
                        padding: '40px',
                        borderRadius: '16px',
                        textAlign: 'center',
                        boxShadow: '0 10px 40px rgba(0, 0, 0, 0.5)',
                        border: '1px solid #2d3548'
                    }}>
                        <div className="loading-spinner" style={{width: '60px', height: '60px', marginBottom: '20px'}}></div>
                        <p style={{fontSize: '1.2em', marginBottom: '10px', fontWeight: '600'}}>Processing...</p>
                        {currentOperation && (
                            <p style={{color: '#9ca3af', fontSize: '1em', maxWidth: '400px'}}>
                                {currentOperation}
                            </p>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

// Render the app
ReactDOM.render(<ThreatModelingApp />, document.getElementById('root'));