// ── Dashboard charts ──────────────────────────────────────────────────────────

function initDashboardCharts(categoryData, monthlyData) {
  renderCategoryChart(categoryData);
  renderMonthlyChart(monthlyData);
}

function renderCategoryChart(data) {
  const canvas = document.getElementById('categoryChart');
  if (!canvas || !data.length) return;

  const COLORS = [
    '#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6',
    '#06b6d4','#f97316','#84cc16','#ec4899','#6366f1',
    '#14b8a6','#f43f5e','#a855f7','#22c55e','#0ea5e9',
  ];

  // Show every real category — no fake "Other" bucket that can't be filtered
  const chart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.category),
      datasets: [{
        data: data.map(d => d.total),
        backgroundColor: data.map((d, i) =>
          d.category === 'Wasted' ? '#ef4444' : COLORS[i % COLORS.length]
        ),
        borderWidth: 2,
        borderColor: '#fff',
        hoverOffset: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: $${ctx.parsed.toFixed(2)}`
          }
        }
      },
      cutout: '60%',
      onClick(e) {
        const pts = chart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, false);
        if (!pts.length) return;
        const cat = data[pts[0].index].category;
        // Navigate to transactions filtered by this category, preserving period
        const params = new URLSearchParams(window.location.search);
        params.set('category', cat);
        window.location.href = '/transactions?' + params.toString();
      },
    }
  });
  canvas.style.cursor = 'pointer';
}

const MONTH_LABELS = ['', 'Jan','Feb','Mar','Apr','May','Jun',
                          'Jul','Aug','Sep','Oct','Nov','Dec'];

function renderMonthlyChart(data) {
  const canvas = document.getElementById('monthlyChart');
  if (!canvas) return;

  if (!data.length) {
    canvas.parentElement.innerHTML = '<p class="text-muted text-center py-3 small">No data for this year yet.</p>';
    return;
  }

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: data.map(d => MONTH_LABELS[parseInt(d.month)]),
      datasets: [
        {
          label: 'Total Spent',
          data: data.map(d => d.total),
          backgroundColor: 'rgba(15,52,96,.7)',
          borderRadius: 6,
        },
        {
          label: 'Wasted',
          data: data.map(d => d.wasted),
          backgroundColor: 'rgba(233,69,96,.7)',
          borderRadius: 6,
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'top',
          labels: { font: { size: 11 }, boxWidth: 12 }
        },
        tooltip: {
          callbacks: {
            label: ctx => ` $${ctx.parsed.y.toFixed(2)}`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: v => '$' + v.toLocaleString(),
            font: { size: 11 }
          },
          grid: { color: '#f0f0f0' }
        },
        x: { grid: { display: false }, ticks: { font: { size: 11 } } }
      }
    }
  });
}
