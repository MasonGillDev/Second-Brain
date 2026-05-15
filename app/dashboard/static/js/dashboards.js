/* Agent Dashboards — list, open, delete, restore */
(function () {
    var grid = document.getElementById('dashboards-grid');
    var archivedGrid = document.getElementById('dashboards-archived-grid');
    var archivedSection = document.getElementById('dashboards-archived-section');
    var refreshBtn = document.getElementById('dashboards-refresh');
    if (!grid) return;

    function load() {
        fetch('/api/dashboards')
            .then(function (r) { return r.json(); })
            .then(function (data) { render(data.active, data.archived); })
            .catch(function (e) { grid.innerHTML = '<p style="color:var(--text-secondary)">Failed to load dashboards.</p>'; });
    }

    function render(active, archived) {
        grid.innerHTML = '';
        if (!active || active.length === 0) {
            grid.innerHTML = '<p style="color:var(--text-secondary);padding:2rem;">No dashboards yet. Ask the agent to create one.</p>';
        } else {
            active.forEach(function (d) {
                grid.appendChild(makeCard(d, false));
            });
        }

        archivedGrid.innerHTML = '';
        if (archived && archived.length > 0) {
            archivedSection.style.display = '';
            archived.forEach(function (d) {
                archivedGrid.appendChild(makeCard(d, true));
            });
        } else {
            archivedSection.style.display = 'none';
        }
    }

    function makeCard(d, isArchived) {
        var card = document.createElement('div');
        card.className = 'dashboard-card' + (isArchived ? ' dashboard-card--archived' : '');
        var name = d.name || d.slug;
        var desc = d.description || '';
        var badges = '';
        if (d.has_api) badges += '<span class="dashboard-badge">API</span>';
        if (d.has_data) badges += '<span class="dashboard-badge">Data</span>';

        card.innerHTML =
            '<div class="dashboard-card-header">' +
                '<h3 class="dashboard-card-title">' + escHtml(name) + '</h3>' +
                '<div class="dashboard-card-badges">' + badges + '</div>' +
            '</div>' +
            '<p class="dashboard-card-desc">' + escHtml(desc) + '</p>' +
            '<div class="dashboard-card-actions"></div>';

        var actions = card.querySelector('.dashboard-card-actions');

        if (!isArchived) {
            var openBtn = document.createElement('a');
            openBtn.className = 'btn-primary btn-sm';
            openBtn.href = '/d/' + d.slug + '/';
            openBtn.target = '_blank';
            openBtn.textContent = 'Open';
            actions.appendChild(openBtn);

            var delBtn = document.createElement('button');
            delBtn.className = 'btn-danger btn-sm';
            delBtn.textContent = 'Archive';
            delBtn.onclick = function () {
                if (!confirm('Archive "' + name + '"?')) return;
                fetch('/api/dashboards/' + d.slug, { method: 'DELETE' })
                    .then(function () { load(); });
            };
            actions.appendChild(delBtn);
        } else {
            var restoreBtn = document.createElement('button');
            restoreBtn.className = 'btn-secondary btn-sm';
            restoreBtn.textContent = 'Restore';
            restoreBtn.onclick = function () {
                fetch('/api/dashboards/' + d.slug + '/restore', { method: 'POST' })
                    .then(function () { load(); });
            };
            actions.appendChild(restoreBtn);
        }

        return card;
    }

    function escHtml(s) {
        var d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    refreshBtn.addEventListener('click', load);

    // Load when tab becomes visible
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-tab="dashboards"]');
        if (btn) setTimeout(load, 50);
    });
})();
