// Global state
let ws = null;
let isRunning = false;
let cachedModels = [];

// DOM Elements
const startBtn = document.getElementById('startBtn');
const clearCacheBtn = document.getElementById('clearCacheBtn');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const cacheStatus = document.getElementById('cacheStatus');
const cacheText = document.getElementById('cacheText');
const progressSection = document.getElementById('progressSection');
const currentModel = document.getElementById('currentModel');
const currentDataset = document.getElementById('currentDataset');
const progressText = document.getElementById('progressText');
const progressFill = document.getElementById('progressFill');
const progressPercentage = document.getElementById('progressPercentage');
const statusMessage = document.getElementById('statusMessage');
const samplePreview = document.getElementById('samplePreview');
const previewIndex = document.getElementById('previewIndex');
const referenceText = document.getElementById('referenceText');
const hypothesisText = document.getElementById('hypothesisText');
const modelsList = document.getElementById('modelsList');
const datasetsList = document.getElementById('datasetsList');
const resultsSection = document.getElementById('resultsSection');
const quickStats = document.getElementById('quickStats');
const resultsTable = document.getElementById('resultsTable');
const modelCards = document.getElementById('modelCards');
const visualizationsSection = document.getElementById('visualizationsSection');
const visualizationsGrid = document.getElementById('visualizationsGrid');
const exampleModal = document.getElementById('exampleModal');
const modalTitle = document.getElementById('modalTitle');
const modalBody = document.getElementById('modalBody');

// Initialize
async function init() {
    console.log('Initializing dashboard...');
    await loadCacheStatus();
    await loadConfig();
    connectWebSocket();
    await checkExistingResults();
}

// Load cache status
async function loadCacheStatus() {
    try {
        const response = await fetch('/api/cache/status');
        const data = await response.json();
        cachedModels = data.cached_models || [];
        
        if (cachedModels.length > 0) {
            cacheText.textContent = `${cachedModels.length} model(s) cached`;
        } else {
            cacheText.textContent = 'No cached results';
        }
    } catch (error) {
        console.error('Error loading cache status:', error);
        cacheText.textContent = 'Cache unavailable';
    }
}

// Clear cache
async function clearCache() {
    if (!confirm('Are you sure you want to clear all cached results?')) {
        return;
    }
    
    try {
        const response = await fetch('/api/cache/clear', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'success') {
            cachedModels = [];
            cacheText.textContent = 'No cached results';
            alert('Cache cleared successfully');
            location.reload();
        }
    } catch (error) {
        console.error('Error clearing cache:', error);
        alert('Failed to clear cache');
    }
}

// Load configuration
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        
        // Display models
        modelsList.innerHTML = config.models
            .map(model => {
                const isCached = cachedModels.includes(model.name);
                const cacheIcon = isCached ? '💾' : '';
                return `
                    <div class="list-item ${model.enabled ? 'enabled' : 'disabled'}">
                        <span>${model.name} ${cacheIcon}</span>
                        <span>${model.enabled ? '✓' : '✗'}</span>
                    </div>
                `;
            })
            .join('');
        
        // Display datasets
        datasetsList.innerHTML = config.datasets
            .map(dataset => `
                <div class="list-item ${dataset.enabled ? 'enabled' : 'disabled'}">
                    <span>${dataset.name}</span>
                    <span>${dataset.enabled ? '✓' : '✗'}</span>
                </div>
            `)
            .join('');
    } catch (error) {
        console.error('Error loading config:', error);
        modelsList.innerHTML = '<div class="error">Failed to load configuration</div>';
        datasetsList.innerHTML = '<div class="error">Failed to load configuration</div>';
    }
}

// Start benchmark
async function startBenchmark() {
    try {
        startBtn.disabled = true;
        const response = await fetch('/api/benchmark/start', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.status === 'started') {
            isRunning = true;
            progressSection.style.display = 'block';
            statusDot.classList.add('active');
            statusText.textContent = 'Running';
        } else {
            alert(data.message);
            startBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error starting benchmark:', error);
        alert('Failed to start benchmark');
        startBtn.disabled = false;
    }
}

// Connect WebSocket
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
        const status = JSON.parse(event.data);
        updateStatus(status);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('WebSocket closed, reconnecting...');
        setTimeout(connectWebSocket, 3000);
    };
}

// Update status from WebSocket
function updateStatus(status) {
    statusText.textContent = status.status || 'Unknown';
    statusMessage.textContent = status.message || '';
    
    if (status.current_model) {
        currentModel.textContent = status.current_model;
    }
    
    if (status.current_dataset) {
        currentDataset.textContent = status.current_dataset;
    }
    
    if (status.progress !== undefined && status.total !== undefined) {
        progressText.textContent = `${status.progress}/${status.total}`;
        const percentage = status.total > 0 ? (status.progress / status.total) * 100 : 0;
        progressFill.style.width = `${percentage}%`;
        progressPercentage.textContent = `${Math.round(percentage)}%`;
    }
    
    // Update sample preview
    if (status.current_sample && status.current_sample.reference) {
        samplePreview.style.display = 'block';
        previewIndex.textContent = `#${status.current_sample.sample_index}`;
        referenceText.textContent = status.current_sample.reference;
        hypothesisText.textContent = status.current_sample.hypothesis || 'Processing...';
    }
    
    if (status.status === 'completed') {
        isRunning = false;
        startBtn.disabled = false;
        statusDot.classList.remove('active');
        samplePreview.style.display = 'none';
        loadResults();
        loadVisualizations();
        loadCacheStatus();
    }
    
    if (status.is_running) {
        progressSection.style.display = 'block';
        statusDot.classList.add('active');
        startBtn.disabled = true;
    }
}

// Load results
async function loadResults() {
    try {
        const response = await fetch('/api/benchmark/results');
        const results = await response.json();
        
        if (Object.keys(results).length === 0) {
            return;
        }
        
        resultsSection.style.display = 'block';
        
        // Create quick stats
        createQuickStats(results);
        
        // Create results table
        createResultsTable(results);
        
        // Create model cards
        createModelCards(results);
        
    } catch (error) {
        console.error('Error loading results:', error);
    }
}

// Create quick stats
function createQuickStats(results) {
    const models = Object.keys(results);
    
    if (models.length === 0) return;
    
    // Calculate overall stats
    let totalSamples = 0;
    let avgWER = 0;
    let avgLatency = 0;
    let bestModel = '';
    let bestWER = Infinity;
    
    models.forEach(modelName => {
        const agg = results[modelName].aggregated;
        totalSamples = agg.total_samples;
        avgWER += agg.wer_mean;
        avgLatency += agg.latency_mean;
        
        if (agg.wer_mean < bestWER) {
            bestWER = agg.wer_mean;
            bestModel = modelName;
        }
    });
    
    avgWER /= models.length;
    avgLatency /= models.length;
    
    quickStats.innerHTML = `
        <div class="stat-card">
            <div class="stat-label">Models Tested</div>
            <div class="stat-value">${models.length}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total Samples</div>
            <div class="stat-value">${totalSamples}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Avg WER</div>
            <div class="stat-value">${avgWER.toFixed(2)}<span class="stat-unit">%</span></div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Avg Latency</div>
            <div class="stat-value">${avgLatency.toFixed(3)}<span class="stat-unit">s</span></div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Best Model</div>
            <div class="stat-value" style="font-size: 1.2rem;">${bestModel}</div>
        </div>
    `;
}

// Create results table
function createResultsTable(results) {
    const modelNames = Object.keys(results);
    
    const headerHTML = `
        <thead>
            <tr>
                <th>Model</th>
                <th>WER (%)</th>
                <th>CER (%)</th>
                <th>Latency (s)</th>
                <th>Throughput</th>
                <th>P95 Lat</th>
                <th>P99 Lat</th>
                <th>Samples</th>
            </tr>
        </thead>
    `;
    
    const bodyHTML = `
        <tbody>
            ${modelNames.map(name => {
                const agg = results[name].aggregated;
                return `
                    <tr>
                        <td><strong>${name}</strong></td>
                        <td>${agg.wer_mean.toFixed(2)} ±${agg.wer_std.toFixed(2)}</td>
                        <td>${agg.cer_mean.toFixed(2)} ±${agg.cer_std.toFixed(2)}</td>
                        <td>${agg.latency_mean.toFixed(3)} ±${agg.latency_std.toFixed(3)}</td>
                        <td>${agg.throughput_mean.toFixed(1)}</td>
                        <td>${agg.latency_p95.toFixed(3)}</td>
                        <td>${agg.latency_p99.toFixed(3)}</td>
                        <td>${agg.total_samples}</td>
                    </tr>
                `;
            }).join('')}
        </tbody>
    `;
    
    resultsTable.innerHTML = headerHTML + bodyHTML;
}

// Create model cards
function createModelCards(results) {
    const modelNames = Object.keys(results);
    
    modelCards.innerHTML = modelNames.map(name => {
        const agg = results[name].aggregated;
        
        return `
            <div class="model-card" onclick="showModelExamples('${name}')">
                <div class="model-card-header">
                    <div class="model-name">${name}</div>
                    <div class="view-examples">View Examples →</div>
                </div>
                <div class="model-metrics">
                    <div class="metric-item">
                        <div class="metric-label">WER</div>
                        <div class="metric-value">${agg.wer_mean.toFixed(2)}%</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">CER</div>
                        <div class="metric-value">${agg.cer_mean.toFixed(2)}%</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Latency</div>
                        <div class="metric-value">${agg.latency_mean.toFixed(3)}s</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Throughput</div>
                        <div class="metric-value">${agg.throughput_mean.toFixed(1)}</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Show model examples in modal
async function showModelExamples(modelName) {
    modalTitle.textContent = `${modelName} - Example Predictions`;
    modalBody.innerHTML = '<div class="loading">Loading examples...</div>';
    exampleModal.style.display = 'block';
    
    try {
        const response = await fetch(`/api/model/${encodeURIComponent(modelName)}/examples?limit=10`);
        const data = await response.json();
        
        if (data.examples && data.examples.length > 0) {
            modalBody.innerHTML = data.examples.map((example, idx) => {
                const werClass = example.wer < 10 ? 'good' : example.wer < 30 ? 'medium' : 'bad';
                
                return `
                    <div class="example-item">
                        <div class="example-header">
                            <div class="example-id">Sample #${idx + 1}</div>
                            <div class="example-wer" style="color: ${example.wer < 10 ? '#000' : example.wer < 30 ? '#4a4a4a' : '#7a7a7a'}">
                                WER: ${example.wer.toFixed(2)}%
                            </div>
                        </div>
                        <div class="example-texts">
                            <div class="example-text">
                                <strong>Reference</strong>
                                ${example.reference}
                            </div>
                            <div class="example-text">
                                <strong>Hypothesis</strong>
                                ${example.hypothesis}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            modalBody.innerHTML = '<div class="loading">No examples available</div>';
        }
    } catch (error) {
        console.error('Error loading examples:', error);
        modalBody.innerHTML = '<div class="loading">Failed to load examples</div>';
    }
}

// Close modal
function closeModal() {
    exampleModal.style.display = 'none';
}

// Close modal on outside click
window.onclick = function(event) {
    if (event.target == exampleModal) {
        closeModal();
    }
}

// Load visualizations
async function loadVisualizations() {
    try {
        const response = await fetch('/api/visualizations');
        const visualizations = await response.json();
        
        if (visualizations.length === 0) {
            return;
        }
        
        visualizationsSection.style.display = 'block';
        
        visualizationsGrid.innerHTML = visualizations.map(viz => {
            if (viz.type === 'html') {
                return `
                    <div class="viz-item">
                        <iframe src="${viz.url}" loading="lazy"></iframe>
                        <div class="viz-title">
                            <span>${viz.name.replace(/_/g, ' ')}</span>
                            <button class="viz-expand-btn" onclick="expandVisualization('${viz.url}', '${viz.name}')">
                                ⛶ Fullscreen
                            </button>
                        </div>
                    </div>
                `;
            } else {
                return `
                    <div class="viz-item">
                        <img src="${viz.url}" alt="${viz.name}" loading="lazy">
                        <div class="viz-title">${viz.name.replace(/_/g, ' ')}</div>
                    </div>
                `;
            }
        }).join('');
    } catch (error) {
        console.error('Error loading visualizations:', error);
    }
}

// Expand visualization to fullscreen
function expandVisualization(url, name) {
    modalTitle.textContent = name.replace(/_/g, ' ');
    modalBody.innerHTML = `
        <iframe src="${url}" style="width: 100%; height: 80vh; border: none;"></iframe>
    `;
    exampleModal.style.display = 'block';
}

// Check for existing results on load
async function checkExistingResults() {
    await loadResults();
    await loadVisualizations();
}

// Toggle configuration
function toggleConfig() {
    const configBody = document.getElementById('configBody');
    const configToggle = document.getElementById('configToggle');
    
    configBody.classList.toggle('collapsed');
    configToggle.classList.toggle('rotated');
}

// Event listeners
startBtn.addEventListener('click', startBenchmark);
clearCacheBtn.addEventListener('click', clearCache);

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // ESC to close modal
    if (e.key === 'Escape' && exampleModal.style.display === 'block') {
        closeModal();
    }
});

// Initialize on page load
init();

console.log('Dashboard script loaded successfully');