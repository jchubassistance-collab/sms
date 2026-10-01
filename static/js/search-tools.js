(() => {
    const normalize = (value) => (value || '').trim().toLocaleLowerCase();

    function filterRows(input, rows) {
        const query = normalize(input.value);
        rows.forEach((row) => {
            const text = row.dataset.search || row.textContent;
            row.hidden = Boolean(query) && !normalize(text).includes(query);
        });
    }

    // The shared header search controls the page's dedicated list filter when one exists.
    document.querySelectorAll('.topbar .search input[type="search"], .reference-top .search input[type="search"]').forEach((input) => {
        const main = input.closest('main') || document;
        const local = main.querySelector('[data-table-search], .list-search, #package-search, .reference-tools input[type="search"]');
        if (local === input) return; // A page may already wire its top search directly.
        if (local && local !== input) {
            input.setAttribute('aria-label', input.getAttribute('aria-label') || 'Rechercher dans cette page');
            input.addEventListener('input', () => {
                local.value = input.value;
                local.dispatchEvent(new Event('input', { bubbles: true }));
            });
            local.addEventListener('input', () => {
                if (input.value !== local.value) input.value = local.value;
            });
            return;
        }

        const rows = [...main.querySelectorAll('tbody tr:not([data-empty])')];
        if (rows.length) {
            input.addEventListener('input', () => filterRows(input, rows));
            return;
        }

        // On composition pages without a list, use the same field to find a destination.
        const links = [...document.querySelectorAll('.shared-sidebar .shared-nav a, .shared-sidebar .shared-subnav a, .reference-sidebar a')];
        if (links.length) input.addEventListener('input', () => {
            const query = normalize(input.value);
            links.forEach((link) => { link.hidden = Boolean(query) && !normalize(link.textContent).includes(query); });
        });
    });

    // Dashboard and contact page filters are not table-tools tables.
    document.querySelectorAll('.reference-tools input[type="search"]').forEach((input) => {
        const rows = [...(input.closest('section') || document).querySelectorAll('tbody tr')];
        input.addEventListener('input', () => filterRows(input, rows));
    });
})();
