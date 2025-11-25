// Cannabis Legislation Tracker - All States Frontend Application

let allBills = [];
let filteredBills = [];
let uniqueStates = new Set();

// Map LegiScan status codes to readable statuses
const STATUS_MAP = {
    1: "Introduced",
    2: "In Committee",
    3: "Passed Chamber",
    4: "Passed Both Chambers",
    5: "Sent to Executive",
    6: "Enacted/Signed",
    7: "Vetoed",
    8: "Failed/Dead",
    9: "Override Attempt"
};

function mapBillStatus(bill) {
    // If status is already a string and not "Unknown", use it
    if (bill.status && typeof bill.status === 'string' && bill.status !== 'Unknown') {
        return bill.status;
    }
    
    // If we have a status_code, map it
    if (bill.status_code && STATUS_MAP[bill.status_code]) {
        return STATUS_MAP[bill.status_code];
    }
    
    // Try to infer from history or other fields
    if (bill.history && bill.history.length > 0) {
        const lastAction = bill.history[0].action || '';
        if (lastAction.toLowerCase().includes('enacted') || lastAction.toLowerCase().includes('signed')) {
            return 'Enacted/Signed';
        }
        if (lastAction.toLowerCase().includes('vetoed')) {
            return 'Vetoed';
        }
        if (lastAction.toLowerCase().includes('passed')) {
            return 'Passed Chamber';
        }
    }
    
    return 'Unknown';
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    loadBillsData();
    setupEventListeners();
});

// Load bills data from JSON file
async function loadBillsData() {
    try {
        const response = await fetch('bills.json');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Map statuses for all bills
        allBills = (data.bills || []).map(bill => ({
            ...bill,
            status: mapBillStatus(bill)
        }));
        filteredBills = [...allBills];
        
        // Extract unique states for filter dropdown
        allBills.forEach(bill => uniqueStates.add(bill.state_name));
        
        populateStateFilter();
        updateLastUpdated(data.last_updated);
        updateStats();
        renderBills();
        
    } catch (error) {
        console.error('Error loading bills data:', error);
        showError('Failed to load legislation data. Please try again later.');
    }
}

// Populate state filter dropdown
function populateStateFilter() {
    const stateFilter = document.getElementById('stateFilter');
    const optgroup = stateFilter.querySelector('optgroup');
    
    // Sort states alphabetically
    const sortedStates = Array.from(uniqueStates)
        .filter(state => state !== 'Federal')
        .sort();
    
    sortedStates.forEach(state => {
        const option = document.createElement('option');
        option.value = state;
        option.textContent = state;
        optgroup.appendChild(option);
    });
}

// Setup event listeners for filters and search
function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    const stateFilter = document.getElementById('stateFilter');
    const statusFilter = document.getElementById('statusFilter');
    const sortOrder = document.getElementById('sortOrder');
    
    searchInput.addEventListener('input', applyFilters);
    stateFilter.addEventListener('change', applyFilters);
    statusFilter.addEventListener('change', applyFilters);
    sortOrder.addEventListener('change', applyFilters);
}

// Apply filters and sorting
function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const stateFilter = document.getElementById('stateFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;
    const sortOrder = document.getElementById('sortOrder').value;
    
    // Filter bills
    filteredBills = allBills.filter(bill => {
        const matchesSearch = 
            bill.title.toLowerCase().includes(searchTerm) ||
            bill.description.toLowerCase().includes(searchTerm) ||
            bill.bill_number.toLowerCase().includes(searchTerm) ||
            bill.state_name.toLowerCase().includes(searchTerm);
        
        const matchesState = 
            stateFilter === 'all' || 
            (stateFilter === 'US' && bill.state_code === 'US') ||
            bill.state_name === stateFilter;
        
        const matchesStatus = 
            statusFilter === 'all' || 
            bill.status.toLowerCase().includes(statusFilter);
        
        return matchesSearch && matchesState && matchesStatus;
    });
    
    // Sort bills
    switch (sortOrder) {
        case 'recent':
            filteredBills.sort((a, b) => {
                const dateA = new Date(a.last_action_date || a.status_date || 0);
                const dateB = new Date(b.last_action_date || b.status_date || 0);
                return dateB - dateA;
            });
            break;
        case 'oldest':
            filteredBills.sort((a, b) => {
                const dateA = new Date(a.last_action_date || a.status_date || 0);
                const dateB = new Date(b.last_action_date || b.status_date || 0);
                return dateA - dateB;
            });
            break;
        case 'state':
            filteredBills.sort((a, b) => {
                if (a.state_name === b.state_name) {
                    const dateA = new Date(a.last_action_date || a.status_date || 0);
                    const dateB = new Date(b.last_action_date || b.status_date || 0);
                    return dateB - dateA;
                }
                return a.state_name.localeCompare(b.state_name);
            });
            break;
        case 'alphabetical':
            filteredBills.sort((a, b) => 
                a.bill_number.localeCompare(b.bill_number)
            );
            break;
    }
    
    renderBills();
}

// Update statistics
function updateStats() {
    const totalBills = allBills.length;
    const totalStates = uniqueStates.size;
    const activeBills = allBills.filter(bill => 
        !bill.status.toLowerCase().includes('enacted') && 
        !bill.status.toLowerCase().includes('vetoed') &&
        !bill.status.toLowerCase().includes('failed') &&
        !bill.status.toLowerCase().includes('dead')
    ).length;
    const analyzedBills = allBills.filter(bill => bill.analysis_url).length;
    
    document.getElementById('totalBills').textContent = totalBills;
    document.getElementById('totalStates').textContent = totalStates;
    document.getElementById('activeBills').textContent = activeBills;
    document.getElementById('analyzedBills').textContent = analyzedBills;
}

// Update last updated timestamp
function updateLastUpdated(timestamp) {
    const date = new Date(timestamp);
    const formatted = date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    document.getElementById('lastUpdated').textContent = formatted;
}

// Render bills to the DOM
function renderBills() {
    const container = document.getElementById('billsContainer');
    
    if (filteredBills.length === 0) {
        container.innerHTML = `
            <div class="no-results">
                <p>No bills found matching your criteria.</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = filteredBills.map(bill => createBillCard(bill)).join('');
}

// Create HTML for a single bill card
function createBillCard(bill) {
    const statusClass = getStatusClass(bill.status);
    const sponsors = bill.sponsors.slice(0, 3); // Show first 3 sponsors
    const hasMoreSponsors = bill.sponsors.length > 3;
    
    // Use last_action_date if available, fallback to status_date
    const dateToUse = bill.last_action_date || bill.status_date;
    let lastActionDate = 'Unknown';
    
    if (dateToUse) {
        const date = new Date(dateToUse);
        if (!isNaN(date.getTime())) {
            lastActionDate = date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        }
    }
    
    // Determine state badge color
    const isFederal = bill.state_code === 'US';
    const stateBadgeClass = isFederal ? 'state-badge-federal' : 'state-badge-state';
    
    return `
        <div class="bill-card">
            <div class="bill-header">
                <div class="bill-title">
                    <div class="bill-meta-top">
                        <span class="state-badge ${stateBadgeClass}">${bill.state_name}</span>
                        <span class="bill-number">${bill.bill_number}</span>
                    </div>
                    <h4>${bill.title}</h4>
                </div>
                <div class="bill-status ${statusClass}">
                    ${bill.status}
                </div>
            </div>
            
            <div class="bill-description">
                ${bill.description}
            </div>
            
            <div class="bill-meta">
                <div class="bill-meta-item">
                    <strong>Last Action:</strong> ${lastActionDate}
                </div>
            </div>
            
            ${sponsors.length > 0 ? `
                <div class="bill-sponsors">
                    <strong>Sponsors:</strong>
                    <div class="sponsor-list">
                        ${sponsors.map(sponsor => `
                            <span class="sponsor-tag">
                                ${sponsor.name}${sponsor.party ? ` (${sponsor.party})` : ''}
                            </span>
                        `).join('')}
                        ${hasMoreSponsors ? `
                            <span class="sponsor-tag">
                                +${bill.sponsors.length - 3} more
                            </span>
                        ` : ''}
                    </div>
                </div>
            ` : ''}
            
            <div class="bill-actions">
                <a href="${bill.url}" target="_blank" class="btn btn-secondary">
                    View on LegiScan
                </a>
                ${bill.analysis_url ? `
                    <a href="${bill.analysis_url}" target="_blank" class="btn btn-analysis">
                        Read CBDT Analysis
                    </a>
                ` : `
                    <span class="btn btn-disabled" title="Analysis coming soon">
                        Analysis Pending
                    </span>
                `}
            </div>
        </div>
    `;
}

// Get CSS class for bill status
function getStatusClass(status) {
    const statusLower = status.toLowerCase();
    
    if (statusLower.includes('introduced')) return 'status-introduced';
    if (statusLower.includes('committee')) return 'status-committee';
    if (statusLower.includes('passed')) return 'status-passed';
    if (statusLower.includes('enacted') || statusLower.includes('signed')) return 'status-enacted';
    
    return 'status-introduced'; // default
}

// Show error message
function showError(message) {
    const container = document.getElementById('billsContainer');
    container.innerHTML = `
        <div class="no-results">
            <p style="color: var(--accent-color);">${message}</p>
        </div>
    `;
}
