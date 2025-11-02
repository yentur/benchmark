// Global state
let ws = null;
let isRunning = false;
let cachedModels = [];
let charts = {};
let currentAudio = null;
let sortStates = {}; // Separate sort state for each dataset

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
const chartsSection = document.getElementById('chartsSection');
const exampleModal = document.getElementById('exampleModal');
const modalTitle = document.getElementById('modalTitle');
const modalBody = document.getElementById('modalBody');

// Chart.js default config
Chart.defaults.font.family = 'Inter, -apple-system, sans-serif';
Chart.defaults.font.size = 13;
Chart.defaults.color = '#000000';
Chart.defaults.plugins.legend.display = true;
Chart.defaults.plugins.legend.position = 'top';
Chart.defaults.scale.grid.color = '#e8e8e8';

// Color scheme
const colors = {
    primary: 'rgba(0, 0, 0, 0.9)',
    dark: 'rgba(26, 26, 26, 0.9)',
    medium: 'rgba(74, 74, 74, 0.9)',
    light: 'rgba(122, 122, 122, 0.9)',
    lighter: 'rgba(160, 160, 160, 0.9)',
    lightest: 'rgba(208, 208, 208, 0.9)'
};

const colorPalette = [
    colors.primary,
    colors.dark,
    colors.medium,
    colors.light,
    colors.lighter,
    colors.lightest
];

// Utility Functions
function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

function formatMetricWithTolerance(mean, std, decimals = 2) {
    if (mean === undefined || mean === null || isNaN(mean)) return '-';
    const meanStr = mean.toFixed(decimals);
    if (std !== undefined && std !== null && std > 0 && !isNaN(std)) {
        return `${meanStr} <span class="tolerance">± ${std.toFixed(decimals)}</span>`;
    }
    return meanStr;
}

function formatNumber(value, decimals = 2) {
    if (value === undefined || value === null || isNaN(value)) return '-';
    return value.toFixed(decimals);
}

// Initialize
async function init() {
    console.log('Initializing dashboard...');
    try {
        await loadCacheStatus();
        await loadConfig();
        connectWebSocket();
        await checkExistingResults();
        console.log('Dashboard initialized successfully');
    } catch (error) {
        console.error('Initialization error:', error);
    }
}

// Load cache status
async function loadCacheStatus() {
    try {
        const response = await fetch('/api/cache/status');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        cachedModels = data.cached_models || [];
        
        if (cachedModels.length > 0) {
            cacheText.textContent = `${cachedModels.length} model(s) cached`;
        } else {
            cacheText.textContent = 'No cached results';
        }
        console.log('Cache status loaded:', cachedModels);
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
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
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
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const config = await response.json();
        
        console.log('Config loaded:', config);
        
        // Display models
        if (config.models && Array.isArray(config.models)) {
            modelsList.innerHTML = config.models
                .map(model => {
                    const isCached = cachedModels.includes(model.name);
                    const cacheIcon = isCached ? '💾' : '';
                    return `
                        <div class="list-item ${model.enabled ? 'enabled' : 'disabled'}">
                            <span>${escapeHtml(model.name)} ${cacheIcon}</span>
                            <span>${model.enabled ? '✓' : '✗'}</span>
                        </div>
                    `;
                })
                .join('');
        }
        
        // Display datasets
        if (config.datasets && Array.isArray(config.datasets)) {
            datasetsList.innerHTML = config.datasets
                .map(dataset => `
                    <div class="list-item ${dataset.enabled ? 'enabled' : 'disabled'}">
                        <span>${escapeHtml(dataset.name)}</span>
                        <span>${dataset.enabled ? '✓' : '✗'}</span>
                    </div>
                `)
                .join('');
        }
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
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'started') {
            isRunning = true;
            progressSection.style.display = 'block';
            statusDot.classList.add('active');
            statusText.textContent = 'Running';
            console.log('Benchmark started');
        } else {
            alert(data.message || 'Failed to start benchmark');
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
        try {
            const status = JSON.parse(event.data);
            updateStatus(status);
        } catch (error) {
            console.error('WebSocket message error:', error);
        }
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
let lastUpdate = 0;
function updateStatus(status) {
    const now = Date.now();
    if (now - lastUpdate < 500 && status.status !== 'completed') {
        return;
    }
    lastUpdate = now;
    
    if (status.status) {
        statusText.textContent = status.status;
    }
    
    if (status.message) {
        statusMessage.textContent = status.message;
    }
    
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
    
    if (status.current_sample && status.current_sample.reference) {
        const newIndex = status.current_sample.sample_index;
        if (previewIndex.textContent !== `#${newIndex}`) {
            samplePreview.style.display = 'block';
            previewIndex.textContent = `#${newIndex}`;
            referenceText.textContent = status.current_sample.reference;
            hypothesisText.textContent = status.current_sample.hypothesis || 'Processing...';
        }
    }
    
    if (status.status === 'completed') {
        isRunning = false;
        startBtn.disabled = false;
        statusDot.classList.remove('active');
        samplePreview.style.display = 'none';
        console.log('Benchmark completed, loading results...');
        loadResults();
        loadChartsData();
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
        console.log('Loading results...');
        const response = await fetch('/api/benchmark/results');
        
        if (!response.ok) {
            console.error('Results API returned:', response.status);
            return;
        }
        
        const results = await response.json();
        console.log('Results loaded:', results);
        console.log('Results type:', typeof results);
        console.log('Results keys:', Object.keys(results));
        
        if (!results || typeof results !== 'object' || Object.keys(results).length === 0) {
            console.log('No results to display');
            resultsSection.style.display = 'none';
            return;
        }
        
        resultsSection.style.display = 'block';
        
        createQuickStats(results);
        createResultsTable(results);
        createModelCards(results);
        
        console.log('Results UI created successfully');
        
    } catch (error) {
        console.error('Error loading results:', error);
        resultsSection.innerHTML = '<div class="error">Failed to load results: ' + error.message + '</div>';
    }
}

// Create quick stats
function createQuickStats(results) {
    try {
        const models = Object.keys(results);
        
        if (models.length === 0) {
            quickStats.innerHTML = '';
            return;
        }
        
        let totalSamples = 0;
        let avgWER = 0;
        let avgLatency = 0;
        let bestModel = '';
        let bestWER = Infinity;
        
        models.forEach(modelName => {
            const modelData = results[modelName];
            if (!modelData || !modelData.aggregated) {
                console.warn(`No aggregated data for model: ${modelName}`);
                return;
            }
            
            const agg = modelData.aggregated;
            totalSamples = agg.total_samples || 0;
            avgWER += agg.wer_mean || 0;
            avgLatency += agg.latency_mean || 0;
            
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
                <div class="stat-value" style="font-size: 1.2rem;">${escapeHtml(bestModel)}</div>
            </div>
        `;
        
        console.log('Quick stats created');
    } catch (error) {
        console.error('Error creating quick stats:', error);
    }
}

// Create results table
function createResultsTable(results) {
    try {
        console.log('Creating results table...');
        const modelNames = Object.keys(results);
        
        if (modelNames.length === 0) {
            resultsTable.innerHTML = '<div class="no-results">No results available</div>';
            return;
        }
        
        // Organize by dataset
        const datasetGroups = {};
        
        modelNames.forEach(name => {
            const modelResults = results[name];
            
            if (!modelResults) {
                console.warn(`No data for model: ${name}`);
                return;
            }
            
            const datasets = modelResults.datasets || {};
            
            Object.keys(datasets).forEach(datasetName => {
                if (!datasetGroups[datasetName]) {
                    datasetGroups[datasetName] = [];
                }
                
                const metrics = datasets[datasetName].metrics || datasets[datasetName];
                datasetGroups[datasetName].push({
                    model: name,
                    wer_mean: metrics.wer_mean,
                    wer_std: metrics.wer_std,
                    cer_mean: metrics.cer_mean,
                    cer_std: metrics.cer_std,
                    latency_mean: metrics.latency_mean,
                    latency_std: metrics.latency_std,
                    throughput_mean: metrics.throughput_mean,
                    latency_p95: metrics.latency_p95,
                    latency_p99: metrics.latency_p99,
                    total_samples: metrics.total_samples
                });
            });
            
            // Add aggregated if no datasets
            if (Object.keys(datasets).length === 0 && modelResults.aggregated) {
                if (!datasetGroups['Overall']) {
                    datasetGroups['Overall'] = [];
                }
                datasetGroups['Overall'].push({
                    model: name,
                    ...modelResults.aggregated
                });
            }
        });
        
        console.log('Dataset groups:', datasetGroups);
        
        const datasetNames = Object.keys(datasetGroups);
        
        if (datasetNames.length === 0) {
            resultsTable.innerHTML = '<div class="no-results">No results available</div>';
            return;
        }
        
        // Initialize sort states for each dataset
        datasetNames.forEach(name => {
            if (!sortStates[name]) {
                sortStates[name] = { column: null, direction: 'asc' };
            }
        });
        
        // Clear previous content
        resultsTable.innerHTML = '';
        
        // Create tabs if multiple datasets
        if (datasetNames.length > 1) {
            const tabsContainer = document.createElement('div');
            tabsContainer.className = 'dataset-tabs-container';
            
            const tabsDiv = document.createElement('div');
            tabsDiv.className = 'dataset-tabs';
            
            datasetNames.forEach((name, idx) => {
                const tab = document.createElement('button');
                tab.className = 'dataset-tab' + (idx === 0 ? ' active' : '');
                tab.setAttribute('data-tab', name);
                tab.onclick = () => switchDatasetTab(name);
                
                tab.innerHTML = `
                    <span class="tab-name">${escapeHtml(name)}</span>
                    <span class="tab-count">${datasetGroups[name].length} models</span>
                `;
                
                tabsDiv.appendChild(tab);
            });
            
            tabsContainer.appendChild(tabsDiv);
            resultsTable.appendChild(tabsContainer);
        }
        
        // Create content container
        const contentContainer = document.createElement('div');
        contentContainer.className = 'dataset-tables';
        
        datasetNames.forEach((name, idx) => {
            const content = document.createElement('div');
            content.className = 'dataset-tab-content' + (idx === 0 ? ' active' : '');
            content.setAttribute('data-dataset', name);
            content.innerHTML = createDatasetTable(name, datasetGroups[name]);
            contentContainer.appendChild(content);
        });
        
        resultsTable.appendChild(contentContainer);
        
        console.log('Results table created successfully');
        
    } catch (error) {
        console.error('Error creating results table:', error);
        resultsTable.innerHTML = '<div class="error">Failed to create table: ' + error.message + '</div>';
    }
}

// Create table for a specific dataset
function createDatasetTable(datasetName, data) {
    const tableId = `table-${datasetName.replace(/[^a-zA-Z0-9]/g, '_')}`;
    
    const rows = data.map(row => `
        <tr>
            <td class="col-model">
                <strong>${escapeHtml(row.model)}</strong>
            </td>
            <td class="col-number">
                ${formatMetricWithTolerance(row.wer_mean, row.wer_std)}
            </td>
            <td class="col-number">
                ${formatMetricWithTolerance(row.cer_mean, row.cer_std)}
            </td>
            <td class="col-number">
                ${formatMetricWithTolerance(row.latency_mean, row.latency_std, 3)}
            </td>
            <td class="col-number">
                ${formatNumber(row.throughput_mean, 1)}
            </td>
            <td class="col-number">
                ${formatNumber(row.latency_p95, 3)}
            </td>
            <td class="col-number">
                ${formatNumber(row.latency_p99, 3)}
            </td>
            <td class="col-number">
                ${row.total_samples || 0}
            </td>
        </tr>
    `).join('');
    
    return `
        <div class="results-table-wrapper">
            <table class="results-table" id="${tableId}">
                <thead>
                    <tr>
                        <th class="sortable col-model" onclick="sortTableByColumn('${escapeHtml(datasetName)}', 'model')">
                            <div class="th-content">
                                <span>Model</span>
                                <span class="sort-icon">⇅</span>
                            </div>
                        </th>
                        <th class="sortable col-number" onclick="sortTableByColumn('${escapeHtml(datasetName)}', 'wer_mean')">
                            <div class="th-content">
                                <span>WER (%)</span>
                                <span class="sort-icon">⇅</span>
                            </div>
                        </th>
                        <th class="sortable col-number" onclick="sortTableByColumn('${escapeHtml(datasetName)}', 'cer_mean')">
                            <div class="th-content">
                                <span>CER (%)</span>
                                <span class="sort-icon">⇅</span>
                            </div>
                        </th>
                        <th class="sortable col-number" onclick="sortTableByColumn('${escapeHtml(datasetName)}', 'latency_mean')">
                            <div class="th-content">
                                <span>Latency (s)</span>
                                <span class="sort-icon">⇅</span>
                            </div>
                        </th>
                        <th class="sortable col-number" onclick="sortTableByColumn('${escapeHtml(datasetName)}', 'throughput_mean')">
                            <div class="th-content">
                                <span>Throughput</span>
                                <span class="sort-icon">⇅</span>
                            </div>
                        </th>
                        <th class="sortable col-number" onclick="sortTableByColumn('${escapeHtml(datasetName)}', 'latency_p95')">
                            <div class="th-content">
                                <span>P95 Latency</span>
                                <span class="sort-icon">⇅</span>
                            </div>
                        </th>
                        <th class="sortable col-number" onclick="sortTableByColumn('${escapeHtml(datasetName)}', 'latency_p99')">
                            <div class="th-content">
                                <span>P99 Latency</span>
                                <span class="sort-icon">⇅</span>
                            </div>
                        </th>
                        <th class="col-number">
                            <div class="th-content">
                                <span>Samples</span>
                            </div>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        </div>
    `;
}

// Switch dataset tab
function switchDatasetTab(tabName) {
    console.log('Switching to tab:', tabName);
    
    // Update tab buttons
    document.querySelectorAll('.dataset-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.dataset-tab-content').forEach(content => {
        content.classList.toggle('active', content.dataset.dataset === tabName);
    });
}

// Sort table by column
function sortTableByColumn(datasetName, columnKey) {
    try {
        console.log('Sorting by:', columnKey, 'for dataset:', datasetName);
        
        const tableId = `table-${datasetName.replace(/[^a-zA-Z0-9]/g, '_')}`;
        const table = document.getElementById(tableId);
        
        if (!table) {
            console.error('Table not found:', tableId);
            return;
        }
        
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Get current sort state
        const state = sortStates[datasetName];
        
        // Toggle direction
        if (state.column === columnKey) {
            state.direction = state.direction === 'asc' ? 'desc' : 'asc';
        } else {
            state.column = columnKey;
            state.direction = 'asc';
        }
        
        // Get column index
        const columnMap = {
            'model': 0,
            'wer_mean': 1,
            'cer_mean': 2,
            'latency_mean': 3,
            'throughput_mean': 4,
            'latency_p95': 5,
            'latency_p99': 6,
            'total_samples': 7
        };
        
        const colIndex = columnMap[columnKey];
        
        if (colIndex === undefined) {
            console.error('Unknown column:', columnKey);
            return;
        }
        
        // Sort rows
        rows.sort((a, b) => {
            let aVal = a.cells[colIndex].textContent.trim();
            let bVal = b.cells[colIndex].textContent.trim();
            
            // Extract number from tolerance format (e.g., "1.23 ± 0.45")
            aVal = aVal.split('±')[0].trim();
            bVal = bVal.split('±')[0].trim();
            
            // Try to parse as number
            const aNum = parseFloat(aVal);
            const bNum = parseFloat(bVal);
            
            let comparison;
            if (!isNaN(aNum) && !isNaN(bNum)) {
                comparison = aNum - bNum;
            } else {
                comparison = aVal.localeCompare(bVal);
            }
            
            return state.direction === 'asc' ? comparison : -comparison;
        });
        
        // Update DOM
        rows.forEach(row => tbody.appendChild(row));
        
        // Update sort icons
        const headers = table.querySelectorAll('th');
        headers.forEach((th, idx) => {
            const icon = th.querySelector('.sort-icon');
            if (icon) {
                if (idx === colIndex) {
                    icon.textContent = state.direction === 'asc' ? '↑' : '↓';
                    th.classList.add('sorted');
                } else {
                    icon.textContent = '⇅';
                    th.classList.remove('sorted');
                }
            }
        });
        
        console.log('Table sorted successfully');
    } catch (error) {
        console.error('Error sorting table:', error);
    }
}

// Create model cards
function createModelCards(results) {
    try {
        const modelNames = Object.keys(results);
        
        if (modelNames.length === 0) {
            modelCards.innerHTML = '';
            return;
        }
        
        modelCards.innerHTML = modelNames.map(name => {
            const modelData = results[name];
            if (!modelData || !modelData.aggregated) {
                return '';
            }
            
            const agg = modelData.aggregated;
            
            return `
                <div class="model-card" onclick="showModelExamples('${escapeHtml(name)}')">
                    <div class="model-card-header">
                        <div class="model-name">${escapeHtml(name)}</div>
                        <div class="view-examples">View Examples →</div>
                    </div>
                    <div class="model-metrics">
                        <div class="metric-item">
                            <div class="metric-label">WER</div>
                            <div class="metric-value">${formatNumber(agg.wer_mean)}%</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">CER</div>
                            <div class="metric-value">${formatNumber(agg.cer_mean)}%</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">Latency</div>
                            <div class="metric-value">${formatNumber(agg.latency_mean, 3)}s</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-label">Throughput</div>
                            <div class="metric-value">${formatNumber(agg.throughput_mean, 1)}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        console.log('Model cards created');
    } catch (error) {
        console.error('Error creating model cards:', error);
    }
}

// Load Charts Data
async function loadChartsData() {
    try {
        console.log('Loading charts data...');
        const response = await fetch('/api/visualization/charts_data.json');
        
        if (!response.ok) {
            console.log('Charts data not available');
            return;
        }
        
        const chartData = await response.json();
        console.log('Charts data loaded:', chartData);
        
        if (!chartData || !chartData.models || chartData.models.length === 0) {
            console.log('No chart data to display');
            return;
        }
        
        chartsSection.style.display = 'block';
        createAllCharts(chartData);
        
        console.log('Charts created successfully');
    } catch (error) {
        console.error('Error loading charts:', error);
    }
}

// Create all charts
function createAllCharts(data) {
    try {
        // Destroy existing charts
        Object.values(charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        charts = {};
        
        if (!data.wer || !data.cer || !data.latency || !data.throughput) {
            console.warn('Incomplete chart data');
            return;
        }
        
        charts.wer = createBarChart('werChart', {
            labels: data.models,
            datasets: [{
                label: 'WER (%)',
                data: data.wer.mean,
                backgroundColor: colorPalette,
                borderColor: colors.primary,
                borderWidth: 2
            }]
        });
        
        charts.cer = createBarChart('cerChart', {
            labels: data.models,
            datasets: [{
                label: 'CER (%)',
                data: data.cer.mean,
                backgroundColor: colorPalette,
                borderColor: colors.primary,
                borderWidth: 2
            }]
        });
        
        charts.latency = createBarChart('latencyChart', {
            labels: data.models,
            datasets: [{
                label: 'Latency (s)',
                data: data.latency.mean,
                backgroundColor: colorPalette,
                borderColor: colors.primary,
                borderWidth: 2
            }]
        });
        
        charts.throughput = createBarChart('throughputChart', {
            labels: data.models,
            datasets: [{
                label: 'Throughput (chars/s)',
                data: data.throughput.mean,
                backgroundColor: colorPalette,
                borderColor: colors.primary,
                borderWidth: 2
            }]
        });
        
        charts.latencyPercentiles = createGroupedBarChart('latencyPercentilesChart', {
            labels: data.models,
            datasets: [
                {
                    label: 'P50',
                    data: data.latency.p50,
                    backgroundColor: colors.primary,
                    borderWidth: 2
                },
                {
                    label: 'P95',
                    data: data.latency.p95,
                    backgroundColor: colors.medium,
                    borderWidth: 2
                },
                {
                    label: 'P99',
                    data: data.latency.p99,
                    backgroundColor: colors.light,
                    borderWidth: 2
                }
            ]
        });
        
        charts.performance = createBarChart('performanceChart', {
            labels: data.models,
            datasets: [{
                label: 'Performance Score',
                data: data.performance_scores,
                backgroundColor: colorPalette,
                borderColor: colors.primary,
                borderWidth: 2
            }]
        });
        
        charts.errorOverview = createGroupedBarChart('errorOverviewChart', {
            labels: data.models,
            datasets: [
                {
                    label: 'WER (%)',
                    data: data.wer.mean,
                    backgroundColor: colors.primary,
                    borderWidth: 2
                },
                {
                    label: 'CER (%)',
                    data: data.cer.mean,
                    backgroundColor: colors.medium,
                    borderWidth: 2
                }
            ]
        });
        
        console.log('All charts created');
    } catch (error) {
        console.error('Error creating charts:', error);
    }
}

// Chart helpers
function createBarChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.warn('Canvas not found:', canvasId);
        return null;
    }
    
    return new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: colors.dark,
                    padding: 12,
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: '#e8e8e8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { maxRotation: 45, minRotation: 0 }
                }
            }
        }
    });
}

function createGroupedBarChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) {
        console.warn('Canvas not found:', canvasId);
        return null;
    }
    
    return new Chart(ctx, {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: {
                    backgroundColor: colors.dark,
                    padding: 12,
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: '#e8e8e8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { maxRotation: 45, minRotation: 0 }
                }
            }
        }
    });
}

// Show model examples with audio
async function showModelExamples(modelName) {
    modalTitle.textContent = `${modelName} - Example Predictions`;
    modalBody.innerHTML = '<div class="loading">Loading examples...</div>';
    exampleModal.style.display = 'block';
    
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }
    
    try {
        const response = await fetch(`/api/model/${encodeURIComponent(modelName)}/examples?limit=10`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.examples && data.examples.length > 0) {
            modalBody.innerHTML = data.examples.map((example, idx) => {
                const audioHTML = example.id ? `
                    <div class="audio-player">
                        <button class="audio-btn" onclick="playAudio('${escapeHtml(example.id)}', this)">
                            ▶ Play Audio
                        </button>
                        <audio id="audio-${escapeHtml(example.id)}" preload="none">
                            <source src="/api/audio/${encodeURIComponent(example.id)}" type="audio/wav">
                        </audio>
                    </div>
                ` : '';
                
                return `
                    <div class="example-item">
                        <div class="example-header">
                            <div class="example-id">Sample #${idx + 1}</div>
                            <div class="example-wer">WER: ${formatNumber(example.wer)}%</div>
                        </div>
                        ${audioHTML}
                        <div class="example-texts">
                            <div class="example-text">
                                <strong>Reference</strong>
                                ${escapeHtml(example.reference)}
                            </div>
                            <div class="example-text">
                                <strong>Hypothesis</strong>
                                ${escapeHtml(example.hypothesis)}
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

// Play audio
function playAudio(sampleId, button) {
    const audio = document.getElementById(`audio-${sampleId}`);
    
    if (!audio) {
        alert('Audio not available');
        return;
    }
    
    if (currentAudio && currentAudio !== audio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        const prevBtn = document.querySelector('.audio-btn.playing');
        if (prevBtn) {
            prevBtn.textContent = '▶ Play Audio';
            prevBtn.classList.remove('playing');
        }
    }
    
    if (audio.paused) {
        audio.play();
        button.textContent = '⏸ Pause';
        button.classList.add('playing');
        currentAudio = audio;
        
        audio.onended = () => {
            button.textContent = '▶ Play Audio';
            button.classList.remove('playing');
            currentAudio = null;
        };
    } else {
        audio.pause();
        button.textContent = '▶ Play Audio';
        button.classList.remove('playing');
        currentAudio = null;
    }
}

// Close modal
function closeModal() {
    exampleModal.style.display = 'none';
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }
}

window.onclick = function(event) {
    if (event.target == exampleModal) {
        closeModal();
    }
}

// Check for existing results
async function checkExistingResults() {
    console.log('Checking for existing results...');
    await loadResults();
    await loadChartsData();
}

// Toggle configuration
function toggleConfig() {
    const configBody = document.getElementById('configBody');
    const configToggle = document.getElementById('configToggle');
    
    if (configBody && configToggle) {
        configBody.classList.toggle('collapsed');
        configToggle.classList.toggle('rotated');
    }
}

// Event listeners
if (startBtn) {
    startBtn.addEventListener('click', startBenchmark);
}

if (clearCacheBtn) {
    clearCacheBtn.addEventListener('click', clearCache);
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && exampleModal && exampleModal.style.display === 'block') {
        closeModal();
    }
});

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

console.log('Dashboard script loaded successfully');