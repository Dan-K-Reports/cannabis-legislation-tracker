// Cannabis Legislation Tracker - Progressive Enhancement Version
// Works with pre-rendered HTML, adds filtering and sorting functionality

let allBillCards = [];

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Get all pre-rendered bill cards
    allBillCards = Array.from(document.querySelectorAll('.bill-card'));
    
    // Setup event listeners for filters
    setupEventListeners();
    
    console.log(`✅ Tracker initialized with ${allBillCards.length} pre-rendered bills`);
});

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
    
    const billsContainer = document.getElementById('billsContainer');
    const noResults = document.getElementById('noResults');
    
    // Filter bills
    let visibleBills = allBillCards.filter(card => {
        const cardText = card.textContent.toLowerCase();
        const matchesSearch = cardText.includes(searchTerm);
        
        const stateCode = card.dataset.stateCode;
        const stateName = card.dataset.state;
        const matchesState = 
            stateFilter === 'all' || 
            (stateFilter === 'US' && stateCode === 'US') ||
            stateName === stateFilter;
        
        const cardStatus = card.dataset.status.toLowerCase();
        const matchesStatus = 
            statusFilter === 'all' || 
            cardStatus.includes(statusFilter);
        
        return matchesSearch && matchesState && matchesStatus;
    });
    
    // Sort bills
    switch (sortOrder) {
        case 'recent':
            visibleBills.sort((a, b) => {
                const dateA = new Date(a.dataset.date || 0);
                const dateB = new Date(b.dataset.date || 0);
                return dateB - dateA;
            });
            break;
        case 'oldest':
            visibleBills.sort((a, b) => {
                const dateA = new Date(a.dataset.date || 0);
                const dateB = new Date(b.dataset.date || 0);
                return dateA - dateB;
            });
            break;
        case 'state':
            visibleBills.sort((a, b) => {
                const stateA = a.dataset.state;
                const stateB = b.dataset.state;
                if (stateA === stateB) {
                    const dateA = new Date(a.dataset.date || 0);
                    const dateB = new Date(b.dataset.date || 0);
                    return dateB - dateA;
                }
                return stateA.localeCompare(stateB);
            });
            break;
        case 'alphabetical':
            visibleBills.sort((a, b) => {
                const billA = a.querySelector('.bill-number').textContent;
                const billB = b.querySelector('.bill-number').textContent;
                return billA.localeCompare(billB);
            });
            break;
    }
    
    // Hide all cards first
    allBillCards.forEach(card => {
        card.style.display = 'none';
    });
    
    // Show and reorder filtered bills
    if (visibleBills.length === 0) {
        noResults.style.display = 'block';
    } else {
        noResults.style.display = 'none';
        
        // Reorder visible bills
        visibleBills.forEach(card => {
            card.style.display = 'block';
            billsContainer.appendChild(card); // Moves to end in new order
        });
    }
}
