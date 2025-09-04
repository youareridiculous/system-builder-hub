// Analytics JavaScript
let currentCursor = null;
let hasMoreEvents = false;
let currentFilters = {};

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadData();
});

// Load all data
async function loadData() {
    await Promise.all([
        loadKPIs(),
        loadUsageData(),
        loadEvents()
    ]);
}

// Load KPI metrics
async function loadKPIs() {
    try {
        showLoading('kpi');
        
        const response = await fetch('/api/analytics/metrics', {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            updateKPICards(data.data);
        } else {
            showError('Failed to load KPI metrics');
        }
    } catch (error) {
        console.error('Error loading KPIs:', error);
        showError('Failed to load KPI metrics');
    } finally {
        hideLoading('kpi');
    }
}

// Update KPI cards
function updateKPICards(metrics) {
    // Signups
    const signups = metrics['auth.user.registered'] || {};
    document.getElementById('kpiSignups').textContent = signups.month || 0;
    
    // Logins
    const logins = metrics['auth.user.login'] || {};
    document.getElementById('kpiLogins').textContent = logins.month || 0;
    
    // Builds
    const builds = metrics['builder.generate.completed'] || {};
    document.getElementById('kpiBuilds').textContent = builds.month || 0;
    
    // API Requests
    const apiRequests = metrics['apikey.request'] || {};
    document.getElementById('kpiApiRequests').textContent = apiRequests.month || 0;
}

// Load usage data for chart
async function loadUsageData() {
    try {
        const fromDate = getFromDate();
        const toDate = new Date().toISOString().split('T')[0];
        const metric = document.getElementById('metricSelect').value;
        
        const response = await fetch(`/api/analytics/usage?from=${fromDate}&to=${toDate}&metric=${metric}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            updateChart(data.data);
        } else {
            showError('Failed to load usage data');
        }
    } catch (error) {
        console.error('Error loading usage data:', error);
        showError('Failed to load usage data');
    }
}

// Update chart
function updateChart(usageData) {
    const canvas = document.getElementById('usageChart');
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const metric = document.getElementById('metricSelect').value;
    const data = usageData[metric] || [];
    
    if (data.length === 0) {
        // Show empty state
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No data available', canvas.width / 2, canvas.height / 2);
        return;
    }
    
    // Set canvas size
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    
    // Find min/max values
    const values = data.map(d => d.count);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = maxValue - minValue || 1;
    
    // Chart dimensions
    const padding = 40;
    const chartWidth = canvas.width - 2 * padding;
    const chartHeight = canvas.height - 2 * padding;
    
    // Draw axes
    ctx.strokeStyle = '#dee2e6';
    ctx.lineWidth = 1;
    
    // X-axis
    ctx.beginPath();
    ctx.moveTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();
    
    // Y-axis
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.stroke();
    
    // Draw data points and lines
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.fillStyle = '#667eea';
    
    ctx.beginPath();
    
    data.forEach((point, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth;
        const y = canvas.height - padding - ((point.count - minValue) / range) * chartHeight;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
        
        // Draw point
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
        ctx.beginPath();
    });
    
    ctx.stroke();
    
    // Draw labels
    ctx.fillStyle = '#495057';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    
    // X-axis labels (dates)
    data.forEach((point, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth;
        const date = new Date(point.date);
        const label = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        ctx.fillText(label, x, canvas.height - padding + 20);
    });
    
    // Y-axis labels
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
        const value = minValue + (i / 5) * range;
        const y = canvas.height - padding - (i / 5) * chartHeight;
        ctx.fillText(Math.round(value).toString(), padding - 10, y + 4);
    }
}

// Load events
async function loadEvents() {
    try {
        showLoading('events');
        
        const params = new URLSearchParams();
        
        // Add filters
        if (currentFilters.from) params.append('from', currentFilters.from);
        if (currentFilters.to) params.append('to', currentFilters.to);
        if (currentFilters.event) params.append('event', currentFilters.event);
        if (currentFilters.source) params.append('source', currentFilters.source);
        if (currentCursor) params.append('cursor', currentCursor);
        
        params.append('limit', '50');
        
        const response = await fetch(`/api/analytics/events?${params}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const data = await response.json();
            updateEventsTable(data.data);
        } else {
            showError('Failed to load events');
        }
    } catch (error) {
        console.error('Error loading events:', error);
        showError('Failed to load events');
    } finally {
        hideLoading('events');
    }
}

// Update events table
function updateEventsTable(data) {
    const tableBody = document.getElementById('eventsTable');
    const emptyState = document.getElementById('eventsEmpty');
    
    if (data.events.length === 0) {
        tableBody.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    
    emptyState.style.display = 'none';
    
    tableBody.innerHTML = data.events.map(event => `
        <tr>
            <td>${formatDateTime(event.ts)}</td>
            <td><code>${event.event}</code></td>
            <td><span class="badge bg-secondary">${event.source}</span></td>
            <td>${event.user_id || '-'}</td>
            <td class="props-cell" title="${JSON.stringify(event.props)}">
                ${Object.keys(event.props).length > 0 ? JSON.stringify(event.props) : '-'}
            </td>
        </tr>
    `).join('');
    
    // Update pagination state
    currentCursor = data.next_cursor;
    hasMoreEvents = data.has_more;
}

// Update filters
function updateFilters() {
    const dateRange = document.getElementById('dateRange').value;
    const eventFilter = document.getElementById('eventFilter').value;
    const sourceFilter = document.getElementById('sourceFilter').value;
    
    currentFilters = {};
    
    if (dateRange === 'custom') {
        // For custom, you could add date pickers
        currentFilters.from = getFromDate();
        currentFilters.to = new Date().toISOString();
    } else if (dateRange !== '') {
        const fromDate = new Date();
        fromDate.setDate(fromDate.getDate() - parseInt(dateRange));
        currentFilters.from = fromDate.toISOString();
        currentFilters.to = new Date().toISOString();
    }
    
    if (eventFilter) currentFilters.event = eventFilter;
    if (sourceFilter) currentFilters.source = sourceFilter;
    
    // Reset pagination
    currentCursor = null;
    hasMoreEvents = false;
    
    // Reload data
    loadUsageData();
    loadEvents();
}

// Pagination functions
function previousPage() {
    // For simplicity, we'll just reload from the beginning
    currentCursor = null;
    loadEvents();
}

function nextPage() {
    if (hasMoreEvents && currentCursor) {
        loadEvents();
    }
}

// Export data
async function exportData() {
    try {
        const params = new URLSearchParams();
        
        // Add current filters
        if (currentFilters.from) params.append('from', currentFilters.from);
        if (currentFilters.to) params.append('to', currentFilters.to);
        if (currentFilters.event) params.append('event', currentFilters.event);
        if (currentFilters.source) params.append('source', currentFilters.source);
        
        const response = await fetch(`/api/analytics/export.csv?${params}`, {
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`,
                'X-Tenant-Slug': getCurrentTenant()
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'analytics_export.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showSuccess('Export completed');
        } else {
            showError('Failed to export data');
        }
    } catch (error) {
        console.error('Error exporting data:', error);
        showError('Failed to export data');
    }
}

// Refresh data
function refreshData() {
    loadData();
}

// Utility functions
function getFromDate() {
    const dateRange = document.getElementById('dateRange').value;
    if (dateRange === 'custom') {
        return new Date().toISOString().split('T')[0];
    }
    
    const fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - parseInt(dateRange || 30));
    return fromDate.toISOString().split('T')[0];
}

function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showLoading(type) {
    if (type === 'events') {
        document.getElementById('eventsLoading').style.display = 'block';
        document.getElementById('eventsEmpty').style.display = 'none';
    }
}

function hideLoading(type) {
    if (type === 'events') {
        document.getElementById('eventsLoading').style.display = 'none';
    }
}

function showSuccess(message) {
    alert('Success: ' + message);
}

function showError(message) {
    alert('Error: ' + message);
}

function getAuthToken() {
    return localStorage.getItem('authToken') || '';
}

function getCurrentTenant() {
    return localStorage.getItem('currentTenant') || 'primary';
}
