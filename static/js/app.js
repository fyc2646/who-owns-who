// Global state
let currentEventId = null;
let people = [];
let activities = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('create-event-btn').addEventListener('click', createEvent);
    document.getElementById('add-person-btn').addEventListener('click', addPerson);
    document.getElementById('activity-form').addEventListener('submit', addActivity);
    document.getElementById('split-strategy').addEventListener('change', handleSplitStrategyChange);
    document.getElementById('compute-settlement-btn').addEventListener('click', computeSettlement);
}

async function createEvent() {
    const name = document.getElementById('event-name').value.trim();
    const currency = document.getElementById('currency').value;
    
    if (!name) {
        showStatus('event-status', 'Please enter an event name', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, currency }),
        });
        
        if (!response.ok) throw new Error('Failed to create event');
        
        const data = await response.json();
        currentEventId = data.event_id;
        
        showStatus('event-status', `Event "${name}" created successfully!`, 'success');
        document.getElementById('people-section').style.display = 'block';
        document.getElementById('activities-section').style.display = 'block';
        document.getElementById('settlement-section').style.display = 'block';
        
        // Load event data
        await loadEvent();
    } catch (error) {
        showStatus('event-status', 'Error creating event: ' + error.message, 'error');
    }
}

async function loadEvent() {
    if (!currentEventId) return;
    
    try {
        const response = await fetch(`/api/event/${currentEventId}`);
        if (!response.ok) throw new Error('Failed to load event');
        
        const data = await response.json();
        people = data.people;
        activities = data.activities;
        
        updatePeopleList();
        updateActivitiesList();
        updatePayerSelect();
        updateParticipantsCheckboxes();
    } catch (error) {
        console.error('Error loading event:', error);
    }
}

async function addPerson() {
    const nameInput = document.getElementById('person-name');
    const name = nameInput.value.trim();
    
    if (!name) {
        alert('Please enter a name');
        return;
    }
    
    if (!currentEventId) {
        alert('Please create an event first');
        return;
    }
    
    try {
        const response = await fetch(`/api/event/${currentEventId}/person`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to add person');
        }
        
        const person = await response.json();
        people.push(person);
        
        nameInput.value = '';
        updatePeopleList();
        updatePayerSelect();
        updateParticipantsCheckboxes();
    } catch (error) {
        alert('Error adding person: ' + error.message);
    }
}

function updatePeopleList() {
    const list = document.getElementById('people-list');
    list.innerHTML = people.map(p => 
        `<li><span>${p.name}</span></li>`
    ).join('');
}

function updatePayerSelect() {
    const select = document.getElementById('activity-payer');
    select.innerHTML = '<option value="">Select payer...</option>' +
        people.map(p => `<option value="${p.name}">${p.name}</option>`).join('');
}

function updateParticipantsCheckboxes() {
    const container = document.getElementById('participants-checkboxes');
    container.innerHTML = people.map(p => 
        `<label><input type="checkbox" name="participant" value="${p.name}"> ${p.name}</label>`
    ).join('');
}

async function addActivity(e) {
    e.preventDefault();
    
    if (!currentEventId) {
        alert('Please create an event first');
        return;
    }
    
    const description = document.getElementById('activity-description').value.trim();
    const amount = parseFloat(document.getElementById('activity-amount').value);
    const payer = document.getElementById('activity-payer').value;
    const splitStrategy = document.getElementById('split-strategy').value;
    
    const participants = Array.from(document.querySelectorAll('input[name="participant"]:checked'))
        .map(cb => cb.value);
    
    if (!description || !amount || !payer || participants.length === 0) {
        alert('Please fill in all required fields');
        return;
    }
    
    const activityData = {
        description,
        amount,
        payer,
        participants,
        split_strategy: splitStrategy,
    };
    
    // Add weights or shares if needed
    if (splitStrategy === 'WEIGHTED') {
        const weights = {};
        document.querySelectorAll('#weights-inputs input').forEach(input => {
            const name = input.dataset.person;
            const weight = parseFloat(input.value);
            if (weight > 0) weights[name] = weight;
        });
        if (Object.keys(weights).length > 0) {
            activityData.weights = weights;
        }
    } else if (splitStrategy === 'FIXED_SHARES') {
        const shares = {};
        document.querySelectorAll('#shares-inputs input').forEach(input => {
            const name = input.dataset.person;
            const share = parseFloat(input.value);
            if (share > 0) shares[name] = share;
        });
        if (Object.keys(shares).length > 0) {
            activityData.shares = shares;
        }
    }
    
    try {
        const response = await fetch(`/api/event/${currentEventId}/activity`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(activityData),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to add activity');
        }
        
        const activity = await response.json();
        activities.push(activity);
        
        // Reset form
        document.getElementById('activity-form').reset();
        updateActivitiesList();
    } catch (error) {
        alert('Error adding activity: ' + error.message);
    }
}

function updateActivitiesList() {
    const list = document.getElementById('activities-list');
    if (activities.length === 0) {
        list.innerHTML = '<li style="color: var(--text-secondary);">No activities yet</li>';
        return;
    }
    
    list.innerHTML = activities.map(a => 
        `<li>
            <div>
                <strong>${a.description}</strong><br>
                <small>${formatCurrency(a.amount)} • Payer: ${a.payer} • Split: ${a.split_strategy}</small>
            </div>
        </li>`
    ).join('');
}

function handleSplitStrategyChange() {
    const strategy = document.getElementById('split-strategy').value;
    const weightsSection = document.getElementById('weights-section');
    const sharesSection = document.getElementById('shares-section');
    
    weightsSection.style.display = strategy === 'WEIGHTED' ? 'block' : 'none';
    sharesSection.style.display = strategy === 'FIXED_SHARES' ? 'block' : 'none';
    
    if (strategy === 'WEIGHTED') {
        updateWeightsInputs();
    } else if (strategy === 'FIXED_SHARES') {
        updateSharesInputs();
    }
}

function updateWeightsInputs() {
    const container = document.getElementById('weights-inputs');
    container.innerHTML = people.map(p => 
        `<div class="input-row">
            <label style="min-width: 100px;">${p.name}:</label>
            <input type="number" data-person="${p.name}" step="0.1" min="0" placeholder="Weight" value="1">
        </div>`
    ).join('');
}

function updateSharesInputs() {
    const container = document.getElementById('shares-inputs');
    container.innerHTML = people.map(p => 
        `<div class="input-row">
            <label style="min-width: 100px;">${p.name}:</label>
            <input type="number" data-person="${p.name}" step="0.01" min="0" placeholder="Amount">
        </div>`
    ).join('');
}

async function computeSettlement() {
    if (!currentEventId) {
        alert('Please create an event first');
        return;
    }
    
    if (activities.length === 0) {
        alert('Please add at least one activity');
        return;
    }
    
    try {
        const response = await fetch(`/api/event/${currentEventId}/settlement`);
        if (!response.ok) throw new Error('Failed to compute settlement');
        
        const data = await response.json();
        displaySettlement(data);
    } catch (error) {
        alert('Error computing settlement: ' + error.message);
    }
}

function displaySettlement(data) {
    // Display summary
    const tbody = document.querySelector('#summary-table tbody');
    tbody.innerHTML = Object.entries(data.summary).map(([name, info]) => {
        const net = parseFloat(info.net);
        const netClass = net > 0 ? 'positive' : net < 0 ? 'negative' : '';
        return `
            <tr>
                <td><strong>${name}</strong></td>
                <td>${formatCurrency(info.paid)}</td>
                <td>${formatCurrency(info.owed)}</td>
                <td class="${netClass}">${formatCurrency(info.net)}</td>
            </tr>
        `;
    }).join('');
    
    // Display transfers
    const transfersList = document.getElementById('transfers-list');
    if (data.transfers.length === 0) {
        transfersList.innerHTML = '<p style="color: var(--text-secondary);">No transfers needed - everyone is settled!</p>';
    } else {
        transfersList.innerHTML = data.transfers.map(t => 
            `<div class="transfer-item">
                <span><strong>${t.from}</strong> <span class="arrow">→</span> <strong>${t.to}</strong></span>
                <span class="amount">${formatCurrency(t.amount)}</span>
            </div>`
        ).join('');
    }
    
    document.getElementById('settlement-results').style.display = 'block';
}

function formatCurrency(amount) {
    const currency = document.getElementById('currency').value;
    const symbols = { USD: '$', EUR: '€', GBP: '£', JPY: '¥' };
    const symbol = symbols[currency] || currency + ' ';
    return symbol + parseFloat(amount).toFixed(2);
}

function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = `status-message ${type}`;
    setTimeout(() => {
        element.className = 'status-message';
    }, 5000);
}

