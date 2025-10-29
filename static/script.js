// Global state
let ws = null;
let isRunning = false;

// DOM Elements
const startBtn = document.getElementById('startBtn');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const progressSection = document.getElementById('progressSection');
const currentModel = document.getElementById('currentModel');
const currentDataset = document.getElementById('currentDataset');
const progressText = document.getElementById('progressText');
const progressFill = document.getElementById('progressFill');
const statusMessage = document.getElementById('statusMessage');
const modelsList = document.getElementById('modelsList');
const datasetsList = document.getElementById('datasetsList');
const resultsSection = document.getElementById('resultsSection');
const resultsTable = document.getElementById('resultsTable');
const visualizationsSection = document.getElementById('visualizationsSection');
const visualizationsGrid = document.getElementById('visualizationsGrid');

// Initialize
async function init() {
    await loadConfig();
    connectWebSocket();
    checkExistingResults();
}

// Load configuration
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        
        // Display models
        modelsList.innerHTML = config.models
            .map(model => `
                <div class="list-item ${model.enabled ? 'enabled' : 'disabled'}">
                    ${model.name}
                    ${model.enabled ? '✓' : '✗'}
                </div>
            `)
            .join('');
        
        // Display datasets
        datasetsList.innerHTML = config.datasets
            .map(dataset => `
                <div class="list-item ${dataset.enabled ? 'enabled' : 'disabled'}">
                    ${dataset.name}
                    ${dataset.enabled ? '✓' : '✗'}
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
    }
    
    if (status.status === 'completed') {
        isRunning = false;
        startBtn.disabled = false;
        statusDot.classList.remove('active');
        loadResults();
        loadVisualizations();
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
        
        // Create results table
        const modelNames = Object.keys(results);
        const tableHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>WER (%)</th>
                        <th>CER (%)</th>
                        <th>Latency (s)</th>
                        <th>Throughput</th>
                        <th>Samples</th>
                    </tr>
                </thead>
                <tbody>
                    ${modelNames.map(name => {
                        const agg = results[name].aggregated;
                        return `
                            <tr>
                                <td><strong>${name}</strong></td>
                                <td>${agg.wer_mean.toFixed(2)}</td>
                                <td>${agg.cer_mean.toFixed(2)}</td>
                                <td>${agg.latency_mean.toFixed(3)}</td>
                                <td>${agg.throughput_mean.toFixed(1)}</td>
                                <td>${agg.total_samples}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        `;
        
        resultsTable.innerHTML = tableHTML;
    } catch (error) {
        console.error('Error loading results:', error);
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
        
        visualizationsGrid.innerHTML = visualizations.map(viz => `
            <div class="viz-item">
                <img src="${viz.url}" alt="${viz.name}" loading="lazy">
                <div class="viz-title">${viz.name.replace(/_/g, ' ')}</div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading visualizations:', error);
    }
}

// Check for existing results on load
async function checkExistingResults() {
    await loadResults();
    await loadVisualizations();
}

// Event listeners
startBtn.addEventListener('click', startBenchmark);

// Initialize on page load
init();