/* Costs dashboard */
(function() {
    const tbody = document.getElementById('costs-tbody');
    const summaryEl = document.getElementById('costs-summary');
    const sinceInput = document.getElementById('costs-since');
    const untilInput = document.getElementById('costs-until');

    // Default date range: last 7 days
    const now = new Date();
    const weekAgo = new Date(now);
    weekAgo.setDate(weekAgo.getDate() - 7);
    sinceInput.value = weekAgo.toISOString().split('T')[0];
    untilInput.value = now.toISOString().split('T')[0];

    window.addEventListener('tab:costs', loadCosts);
    document.getElementById('costs-refresh').addEventListener('click', loadCosts);

    async function loadCosts() {
        const since = sinceInput.value;
        const until = untilInput.value;
        const qs = `since=${since}&until=${until}`;

        const [summary, bySource, calls] = await Promise.all([
            api(`/api/costs/summary?${qs}&group_by=day`),
            api(`/api/costs/by-source?${qs}`),
            api(`/api/costs/calls?${qs}&limit=50`),
        ]);

        if (summary) renderSummary(summary);
        if (summary) renderBarChart(summary.breakdown);
        if (bySource) renderDonut(bySource.sources);
        if (calls) renderTable(calls.calls);
    }

    function renderSummary(data) {
        const t = data.totals;
        // Compute today/week/month from breakdown
        const today = new Date().toISOString().split('T')[0];
        const todayCost = data.breakdown
            .filter(d => d.label === today)
            .reduce((s, d) => s + d.cost_usd, 0);

        summaryEl.innerHTML = `
            <div class="cost-card">
                <div class="cost-value">$${todayCost.toFixed(4)}</div>
                <div class="cost-label">Today</div>
            </div>
            <div class="cost-card">
                <div class="cost-value">$${t.cost_usd.toFixed(4)}</div>
                <div class="cost-label">Selected Range</div>
            </div>
            <div class="cost-card">
                <div class="cost-value">${formatTokens(t.input_tokens)}</div>
                <div class="cost-label">Input Tokens</div>
            </div>
            <div class="cost-card">
                <div class="cost-value">${formatTokens(t.output_tokens)}</div>
                <div class="cost-label">Output Tokens</div>
            </div>
            <div class="cost-card">
                <div class="cost-value">${t.call_count}</div>
                <div class="cost-label">API Calls</div>
            </div>
        `;
    }

    function formatTokens(n) {
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
        return n.toString();
    }

    function renderBarChart(breakdown) {
        const svg = d3.select('#costs-bar-svg');
        svg.selectAll('*').remove();

        if (!breakdown || breakdown.length === 0) {
            svg.attr('width', 0).attr('height', 0);
            return;
        }

        const container = document.getElementById('costs-chart-daily');
        const width = container.clientWidth - 40;
        const height = 200;
        const margin = { top: 10, right: 10, bottom: 30, left: 50 };
        const innerW = width - margin.left - margin.right;
        const innerH = height - margin.top - margin.bottom;

        svg.attr('width', width).attr('height', height);

        const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        const x = d3.scaleBand()
            .domain(breakdown.map(d => d.label))
            .range([0, innerW])
            .padding(0.3);

        const y = d3.scaleLinear()
            .domain([0, d3.max(breakdown, d => d.cost_usd) || 0.001])
            .nice()
            .range([innerH, 0]);

        // Bars
        g.selectAll('rect')
            .data(breakdown)
            .join('rect')
            .attr('x', d => x(d.label))
            .attr('y', d => y(d.cost_usd))
            .attr('width', x.bandwidth())
            .attr('height', d => innerH - y(d.cost_usd))
            .attr('rx', 3)
            .attr('fill', 'var(--accent)');

        // X axis
        g.append('g')
            .attr('transform', `translate(0,${innerH})`)
            .call(d3.axisBottom(x).tickFormat(d => d.slice(5)))
            .selectAll('text')
            .attr('fill', 'var(--text-tertiary)')
            .style('font-size', '10px');

        // Y axis
        g.append('g')
            .call(d3.axisLeft(y).ticks(4).tickFormat(d => '$' + d.toFixed(3)))
            .selectAll('text')
            .attr('fill', 'var(--text-tertiary)')
            .style('font-size', '10px');

        // Style axis lines
        svg.selectAll('.domain, .tick line').attr('stroke', 'var(--border)');
    }

    function renderDonut(sources) {
        const svg = d3.select('#costs-donut-svg');
        svg.selectAll('*').remove();

        if (!sources || sources.length === 0) {
            svg.attr('width', 0).attr('height', 0);
            return;
        }

        const size = 180;
        const radius = size / 2;
        const innerRadius = radius * 0.55;

        svg.attr('width', size + 120).attr('height', size);

        const g = svg.append('g').attr('transform', `translate(${radius},${radius})`);

        const colors = d3.scaleOrdinal()
            .domain(sources.map(s => s.source))
            .range(['#2563EB', '#7E22CE', '#16A34A', '#F59E0B', '#EF4444', '#64748B', '#0EA5E9', '#D946EF']);

        const pie = d3.pie().value(d => d.cost_usd).sort(null);
        const arc = d3.arc().innerRadius(innerRadius).outerRadius(radius - 2);

        g.selectAll('path')
            .data(pie(sources))
            .join('path')
            .attr('d', arc)
            .attr('fill', d => colors(d.data.source))
            .attr('stroke', 'var(--bg-surface)')
            .attr('stroke-width', 2);

        // Legend
        const legend = svg.append('g')
            .attr('transform', `translate(${size + 10}, 10)`);

        sources.forEach((s, i) => {
            const row = legend.append('g').attr('transform', `translate(0, ${i * 20})`);
            row.append('rect')
                .attr('width', 10).attr('height', 10).attr('rx', 2)
                .attr('fill', colors(s.source));
            row.append('text')
                .attr('x', 16).attr('y', 9)
                .attr('fill', 'var(--text-secondary)')
                .style('font-size', '11px')
                .text(`${s.source} $${s.cost_usd.toFixed(4)}`);
        });
    }

    function renderTable(calls) {
        if (!calls || calls.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-tertiary)">No API calls recorded yet</td></tr>';
            return;
        }

        tbody.innerHTML = calls.map(c => {
            const dt = new Date(c.timestamp * 1000);
            const time = dt.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
            const model = c.model.replace('claude-', '').replace(/-\d{8}$/, '');
            return `<tr>
                <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary)">${time}</td>
                <td><span class="source-badge source-${c.source}">${c.source}</span></td>
                <td style="font-family:var(--font-mono);font-size:11px">${model}</td>
                <td style="font-family:var(--font-mono);font-size:11px">${formatTokens(c.input_tokens)}</td>
                <td style="font-family:var(--font-mono);font-size:11px">${formatTokens(c.output_tokens)}</td>
                <td style="font-family:var(--font-mono);font-size:11px">$${c.cost_usd.toFixed(4)}</td>
                <td style="text-align:center">${c.tool_calls_count || '-'}</td>
            </tr>`;
        }).join('');
    }
})();
