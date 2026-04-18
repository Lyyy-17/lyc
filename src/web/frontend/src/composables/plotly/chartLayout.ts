export function getChartLayoutBase(title: string) {
  return {
  title: { text: title, font: { color: '#06b6d4', size: 14, family: 'Orbitron, sans-serif' } },
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#94a3b8', family: 'JetBrains Mono, monospace' },
  margin: { l: 40, r: 20, t: 50, b: 30 },
  xaxis: { showgrid: false, zeroline: false },
  yaxis: { showgrid: false, zeroline: false }
  }
}

