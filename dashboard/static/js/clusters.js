/* D3.js memory cluster visualization */
(function() {
    const svg = d3.select('#cluster-svg');
    const detail = document.getElementById('cluster-detail');
    const thresholdInput = document.getElementById('cluster-threshold');
    const thresholdVal = document.getElementById('cluster-threshold-val');
    const collectionSelect = document.getElementById('cluster-collection');
    let allData = null;
    let simulation = null;

    const CATEGORY_COLORS = {
        user_fact: '#00d4ff',
        preference: '#d2a8ff',
        decision: '#ffb347',
        project_context: '#3fb950',
        general: '#8b949e',
        auto_extracted: '#58a6ff',
        agent_stored: '#79c0ff',
        consolidated: '#f0883e',
    };

    thresholdInput.addEventListener('input', () => {
        thresholdVal.textContent = thresholdInput.value;
        if (allData) renderGraph(allData, parseFloat(thresholdInput.value));
    });

    document.getElementById('cluster-refresh').addEventListener('click', loadClusters);
    window.addEventListener('tab:clusters', loadClusters);

    async function loadClusters() {
        const col = collectionSelect.value;
        const data = await api(`/api/memory/clusters?collection=${col}&threshold=0.2`);
        if (!data) return;
        allData = data;
        renderGraph(data, parseFloat(thresholdInput.value));
    }

    function renderGraph(data, threshold) {
        svg.selectAll('*').remove();
        if (!data.nodes.length) return;

        const rect = svg.node().getBoundingClientRect();
        const width = rect.width;
        const height = rect.height;

        // Filter edges by threshold
        const edges = data.edges.filter(e => e.similarity >= threshold);

        // Create link and node maps
        const nodeMap = new Map(data.nodes.map(n => [n.id, { ...n }]));
        const links = edges.map(e => ({
            source: e.source,
            target: e.target,
            similarity: e.similarity,
        }));

        const nodes = data.nodes.map(n => ({ ...n }));

        // Defs for glow
        const defs = svg.append('defs');
        const filter = defs.append('filter').attr('id', 'glow');
        filter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur');
        const merge = filter.append('feMerge');
        merge.append('feMergeNode').attr('in', 'blur');
        merge.append('feMergeNode').attr('in', 'SourceGraphic');

        const g = svg.append('g');

        // Zoom
        svg.call(d3.zoom()
            .scaleExtent([0.3, 4])
            .on('zoom', (e) => g.attr('transform', e.transform))
        );

        // Links
        const link = g.selectAll('.link')
            .data(links)
            .join('line')
            .attr('class', 'link')
            .attr('stroke', 'rgba(0, 212, 255, 0.15)')
            .attr('stroke-width', d => d.similarity * 3);

        // Nodes
        const node = g.selectAll('.node')
            .data(nodes)
            .join('circle')
            .attr('class', 'node')
            .attr('r', d => Math.max(5, Math.min(18, 5 + (d.access_count || 0) * 2)))
            .attr('fill', d => CATEGORY_COLORS[d.category] || CATEGORY_COLORS.general)
            .attr('opacity', 0.8)
            .attr('filter', 'url(#glow)')
            .attr('cursor', 'pointer')
            .call(d3.drag()
                .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
                .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
                .on('end', (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
            );

        // Hover effects
        node.on('mouseover', function(e, d) {
            d3.select(this).attr('opacity', 1).attr('r', d => Math.max(7, Math.min(22, 7 + (d.access_count || 0) * 2)));
            link.attr('stroke', l => (l.source.id === d.id || l.target.id === d.id) ? 'rgba(0, 212, 255, 0.5)' : 'rgba(0, 212, 255, 0.08)');
        }).on('mouseout', function() {
            d3.select(this).attr('opacity', 0.8).attr('r', d => Math.max(5, Math.min(18, 5 + (d.access_count || 0) * 2)));
            link.attr('stroke', 'rgba(0, 212, 255, 0.15)');
        }).on('click', (e, d) => {
            document.getElementById('cluster-detail-id').textContent = d.id;
            document.getElementById('cluster-detail-text').textContent = d.text;
            const catEl = document.getElementById('cluster-detail-cat');
            catEl.textContent = d.category;
            catEl.className = 'badge cat-' + d.category;
            detail.style.display = '';
        });

        // Simulation
        simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(d => (1 - d.similarity) * 200 + 40))
            .force('charge', d3.forceManyBody().strength(-80))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide(15))
            .on('tick', () => {
                link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
                node.attr('cx', d => d.x).attr('cy', d => d.y);
            });
    }
})();
