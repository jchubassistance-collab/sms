(() => {
    document.addEventListener('click', (event) => {
        const mobileNavToggle = event.target.closest('[data-mobile-nav-toggle]');
        if (mobileNavToggle) {
            const sidebar = mobileNavToggle.closest('.shared-sidebar');
            const isOpen = sidebar?.dataset.mobileOpen === 'true';
            if (!sidebar) return;
            sidebar.dataset.mobileOpen = String(!isOpen);
            mobileNavToggle.setAttribute('aria-expanded', String(!isOpen));
            mobileNavToggle.setAttribute('aria-label', isOpen ? 'Ouvrir le menu de navigation' : 'Fermer le menu de navigation');
            return;
        }
        if (!event.target.closest('.shared-sidebar')) {
            document.querySelectorAll('.shared-sidebar[data-mobile-open="true"]').forEach((sidebar) => {
                sidebar.dataset.mobileOpen = 'false';
                const toggle = sidebar.querySelector('[data-mobile-nav-toggle]');
                toggle?.setAttribute('aria-expanded', 'false');
                toggle?.setAttribute('aria-label', 'Ouvrir le menu de navigation');
            });
        }
        const notificationTrigger = event.target.closest('[data-notification-open]');
        if (notificationTrigger) {
            const root = notificationTrigger.closest('.account-notifications');
            const menu = root?.querySelector('[data-notification-menu]');
            if (!menu) return;
            document.querySelectorAll('[data-profile-menu]:not([hidden])').forEach((openMenu) => {
                openMenu.hidden = true;
                openMenu.closest('.account-profile')?.querySelector('[data-profile-open]')?.setAttribute('aria-expanded', 'false');
            });
            document.querySelectorAll('[data-notification-menu]:not([hidden])').forEach((openMenu) => {
                openMenu.hidden = true;
                openMenu.closest('.account-notifications')?.querySelector('[data-notification-open]')?.setAttribute('aria-expanded', 'false');
            });
            const shouldOpen = menu.hidden;
            menu.hidden = !shouldOpen;
            if (shouldOpen) {
                const triggerRect = notificationTrigger.getBoundingClientRect();
                const menuHeight = menu.getBoundingClientRect().height;
                menu.style.top = `${Math.max(12, Math.min(triggerRect.bottom + 8, window.innerHeight - menuHeight - 12))}px`;
                menu.style.right = `${Math.max(12, window.innerWidth - triggerRect.right)}px`;
            }
            notificationTrigger.setAttribute('aria-expanded', String(shouldOpen));
            return;
        }
        if (!event.target.closest('.account-notifications')) {
            document.querySelectorAll('[data-notification-menu]:not([hidden])').forEach((menu) => {
                menu.hidden = true;
                menu.closest('.account-notifications')?.querySelector('[data-notification-open]')?.setAttribute('aria-expanded', 'false');
            });
        }
        const profileTrigger = event.target.closest('[data-profile-open]');
        if (profileTrigger) {
            const profile = profileTrigger.closest('.account-profile');
            const menu = profile?.querySelector('[data-profile-menu]');
            if (!menu) return;
            const shouldOpen = menu.hidden;
            document.querySelectorAll('[data-profile-menu]:not([hidden])').forEach((openMenu) => {
                openMenu.hidden = true;
                openMenu.closest('.account-profile')?.querySelector('[data-profile-open]')?.setAttribute('aria-expanded', 'false');
            });
            menu.hidden = !shouldOpen;
            if (shouldOpen) {
                const triggerRect = profileTrigger.getBoundingClientRect();
                const menuHeight = menu.getBoundingClientRect().height;
                menu.style.top = `${Math.max(12, Math.min(triggerRect.bottom + 8, window.innerHeight - menuHeight - 12))}px`;
                menu.style.right = `${Math.max(12, window.innerWidth - triggerRect.right)}px`;
            }
            profileTrigger.setAttribute('aria-expanded', String(shouldOpen));
            return;
        }
        if (!event.target.closest('.account-profile')) {
            document.querySelectorAll('[data-profile-menu]:not([hidden])').forEach((menu) => {
                menu.hidden = true;
                menu.closest('.account-profile')?.querySelector('[data-profile-open]')?.setAttribute('aria-expanded', 'false');
            });
        }
        const packageToggle = event.target.closest('#sidebar-package-toggle');
        if (packageToggle) {
            const nav = packageToggle.closest('.shared-nav');
            const submenu = nav ? nav.nextElementSibling : null;
            if (!submenu) return;
            const expanded = packageToggle.getAttribute('aria-expanded') === 'true';
            packageToggle.setAttribute('aria-expanded', String(!expanded));
            submenu.hidden = expanded;
            submenu.style.display = expanded ? 'none' : 'grid';
            return;
        }
        const contactToggle = event.target.closest('#contact-toggle');
        if (contactToggle) {
            const submenu = document.getElementById('contact-submenu');
            const expanded = contactToggle.getAttribute('aria-expanded') === 'true';
            contactToggle.setAttribute('aria-expanded', String(!expanded));
            submenu.hidden = expanded;
            return;
        }
        const messageToggle = event.target.closest('#message-toggle');
        if (messageToggle) {
            const submenu = document.getElementById('message-submenu');
            const expanded = messageToggle.getAttribute('aria-expanded') === 'true';
            messageToggle.setAttribute('aria-expanded', String(!expanded));
            submenu.hidden = expanded;
            return;
        }
        const scheduleToggle = event.target.closest('#schedule-toggle');
        if (scheduleToggle) {
            const submenu = document.getElementById('schedule-submenu');
            const expanded = scheduleToggle.getAttribute('aria-expanded') === 'true';
            scheduleToggle.setAttribute('aria-expanded', String(!expanded));
            submenu.hidden = expanded;
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;
        document.querySelectorAll('[data-profile-menu]:not([hidden])').forEach((menu) => {
            menu.hidden = true;
            const trigger = menu.closest('.account-profile')?.querySelector('[data-profile-open]');
            trigger?.setAttribute('aria-expanded', 'false');
            trigger?.focus();
        });
        document.querySelectorAll('[data-notification-menu]:not([hidden])').forEach((menu) => {
            menu.hidden = true;
            const trigger = menu.closest('.account-notifications')?.querySelector('[data-notification-open]');
            trigger?.setAttribute('aria-expanded', 'false');
            trigger?.focus();
        });
        document.querySelectorAll('.shared-sidebar[data-mobile-open="true"]').forEach((sidebar) => {
            sidebar.dataset.mobileOpen = 'false';
            const toggle = sidebar.querySelector('[data-mobile-nav-toggle]');
            toggle?.setAttribute('aria-expanded', 'false');
            toggle?.setAttribute('aria-label', 'Ouvrir le menu de navigation');
            toggle?.focus();
        });
    });
})();
