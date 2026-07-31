const engineSelect = document.getElementById('engineSelect');
const resultArea = document.getElementById('resultArea');
const loadingMsg = document.getElementById('loadingMsg');
const errorMsg = document.getElementById('errorMsg');

const currentCycleEl = document.getElementById('currentCycle');
const predictedRulEl = document.getElementById('predictedRul');
const statusCard = document.getElementById('statusCard');
const statusMessageEl = document.getElementById('statusMessage');

let sensorChart = null;

engineSelect.addEventListener('change', async () => {
    const engineId = engineSelect.value;

    resultArea.classList.add('hidden');
    errorMsg.classList.add('hidden');

    if (!engineId) return;

    loadingMsg.classList.remove('hidden');

    try {
        const response = await fetch(`/predict/${engineId}`);
        if (!response.ok) throw new Error('Prediction failed');

        const data = await response.json();

        loadingMsg.classList.add('hidden');
        resultArea.classList.remove('hidden');

        // Update cards
        currentCycleEl.textContent = data.current_cycle;
        predictedRulEl.textContent = data.predicted_rul;
        statusMessageEl.textContent = data.message;

        statusCard.classList.remove('healthy', 'warning', 'critical');
        statusCard.classList.add(data.status);

        // Update chart
        renderChart(data.sensor_trend);

    } catch (err) {
        loadingMsg.classList.add('hidden');
        errorMsg.classList.remove('hidden');
        console.error(err);
    }
});

function renderChart(trend) {
    const ctx = document.getElementById('sensorChart').getContext('2d');

    if (sensorChart) {
        sensorChart.destroy();
    }

    sensorChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trend.cycles,
            datasets: [
                {
                    label: 'T24 (Temp)',
                    data: trend.T24,
                    borderColor: '#60a5fa',
                    backgroundColor: 'transparent',
                    tension: 0.2,
                    pointRadius: 0
                },
                {
                    label: 'T50 (Temp)',
                    data: trend.T50,
                    borderColor: '#f472b6',
                    backgroundColor: 'transparent',
                    tension: 0.2,
                    pointRadius: 0
                },
                {
                    label: 'Ps30 (Pressure)',
                    data: trend.Ps30,
                    borderColor: '#34d399',
                    backgroundColor: 'transparent',
                    tension: 0.2,
                    pointRadius: 0
                },
                {
                    label: 'Nc (Core Speed)',
                    data: trend.Nc,
                    borderColor: '#fbbf24',
                    backgroundColor: 'transparent',
                    tension: 0.2,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: {
                    title: { display: true, text: 'Cycle', color: '#94a3b8' },
                    ticks: { color: '#94a3b8' },
                    grid: { color: '#334155' }
                },
                y: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: '#334155' }
                }
            },
            plugins: {
                legend: { labels: { color: '#e2e8f0' } }
            }
        }
    });
}
