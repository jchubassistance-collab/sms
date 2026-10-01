document.querySelectorAll('[data-table-tools]').forEach((container) => {
    const table = container.querySelector('[data-data-table]');
    const body = table?.tBodies[0];
    if (!table || !body) return;

    const rows = [...body.querySelectorAll('[data-row]')];
    const emptyRow = body.querySelector('[data-empty]');
    const search = container.querySelector('[data-table-search]');
    const pageSize = container.querySelector('[data-page-size]');
    const dateFrom = container.querySelector('[data-date-from]');
    const dateTo = container.querySelector('[data-date-to]');
    const datePeriod = container.querySelector('[data-date-period]');
    const methodFilter = container.querySelector('[data-filter-method]');
    const info = container.querySelector('[data-table-info]');
    const previous = container.querySelector('[data-page-prev]');
    const next = container.querySelector('[data-page-next]');
    let currentPage = 1;
    let matchingRows = rows;

    function updateTable(resetPage = true) {
        if (resetPage) currentPage = 1;
        const query = search?.value.trim().toLocaleLowerCase() || '';
        let from = dateFrom?.value || '';
        let to = dateTo?.value || '';
        if (datePeriod && datePeriod.value !== 'custom') {
            const today = new Date();
            const asDateString = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
            to = asDateString(today);
            if (datePeriod.value === 'week') {
                const weekStart = new Date(today);
                weekStart.setDate(today.getDate() - ((today.getDay() + 6) % 7));
                from = asDateString(weekStart);
            } else if (datePeriod.value === 'month') {
                from = asDateString(new Date(today.getFullYear(), today.getMonth(), 1));
            } else if (/^\d+$/.test(datePeriod.value)) {
                const start = new Date(today);
                start.setDate(today.getDate() - Number(datePeriod.value));
                from = asDateString(start);
            } else {
                from = '';
                to = '';
            }
        }
        const method = methodFilter?.value || '';

        matchingRows = rows.filter((row) => {
            const textMatches = !query || (row.dataset.search || row.textContent).toLocaleLowerCase().includes(query);
            const date = row.dataset.date || '';
            const fromMatches = !from || !date || date >= from;
            const toMatches = !to || !date || date <= to;
            const methodMatches = !method || method === 'all' || (row.dataset.method || '').includes(method);
            return textMatches && fromMatches && toMatches && methodMatches;
        });

        const size = Number(pageSize?.value) || matchingRows.length || 10;
        const pageCount = Math.max(1, Math.ceil(matchingRows.length / size));
        currentPage = Math.min(currentPage, pageCount);
        const first = matchingRows.length ? (currentPage - 1) * size : 0;
        const end = Math.min(first + size, matchingRows.length);
        const visibleRows = new Set(matchingRows.slice(first, end));

        rows.forEach((row) => { row.hidden = !visibleRows.has(row); });
        if (emptyRow) emptyRow.hidden = matchingRows.length > 0;
        if (info) info.textContent = `Affichage de ${matchingRows.length ? first + 1 : 0} à ${end} sur ${matchingRows.length} éléments`;
        if (previous) previous.disabled = currentPage <= 1 || matchingRows.length === 0;
        if (next) next.disabled = currentPage >= pageCount || matchingRows.length === 0;
    }

    [search, pageSize, dateFrom, dateTo, datePeriod, methodFilter].filter(Boolean).forEach((control) => {
        control.addEventListener('input', () => updateTable());
        control.addEventListener('change', () => updateTable());
    });
    previous?.addEventListener('click', () => { currentPage -= 1; updateTable(false); });
    next?.addEventListener('click', () => { currentPage += 1; updateTable(false); });
    container.querySelector('[data-table-export]')?.addEventListener('click', () => {
        const headers = [...table.tHead.rows[0].cells].map((cell) => cell.innerText.trim());
        const csv = [headers, ...matchingRows.map((row) => [...row.cells].map((cell) => cell.innerText.trim()))]
            .map((values) => values.map((value) => `"${value.replaceAll('"', '""')}"`).join(','))
            .join('\r\n');
        const file = new Blob(['\ufeff', csv], {type: 'text/csv;charset=utf-8'});
        const url = URL.createObjectURL(file);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${container.dataset.exportName || 'export'}.csv`;
        link.click();
        URL.revokeObjectURL(url);
    });

    updateTable();
});