(function () {
    // ── Configuration ────────────────────────────────────────────────────────
    var AUTO_REFRESH_INTERVAL_MS = 10000;  // 10 seconds
    var CLAIM_DELAY_MS           = 500;    // ms to wait after selectMaterial() before looking for Assign btn

    // ── Storage keys (must not collide with Naviga's existing keys) ──────────
    var KEY_AUTO_REFRESH = 'naviga_auto_refresh';
    var KEY_AUTO_CLAIM   = 'naviga_auto_claim';

    // ── Internal state ───────────────────────────────────────────────────────
    var refreshTimer      = null;
    var claimObserver     = null;
    var assignObserver    = null;
    var lastRefreshTime   = null;
    var statusEl          = null;
    var claimInProgress   = false;  // prevent re-entrancy if multiple rows appear

    // ── Settings persistence ─────────────────────────────────────────────────
    function loadSettings() {
        var r = localStorage.getItem(KEY_AUTO_REFRESH);
        var c = localStorage.getItem(KEY_AUTO_CLAIM);
        return {
            autoRefresh: r === null ? true  : r === 'true',
            autoClaim:   c === null ? false : c === 'true'
        };
    }

    function saveSettings(autoRefresh, autoClaim) {
        localStorage.setItem(KEY_AUTO_REFRESH, autoRefresh ? 'true' : 'false');
        localStorage.setItem(KEY_AUTO_CLAIM,   autoClaim   ? 'true' : 'false');
    }

    // ── Status display ───────────────────────────────────────────────────────
    function updateStatus() {
        if (!statusEl) return;
        var settings = loadSettings();
        if (!settings.autoRefresh) {
            statusEl.textContent = 'Auto-refresh: OFF';
            return;
        }
        if (!lastRefreshTime) {
            statusEl.textContent = 'Auto-refresh: ON';
            return;
        }
        var elapsed = Math.floor((Date.now() - lastRefreshTime) / 1000);
        statusEl.textContent = 'Auto-refresh: ON — last: ' + elapsed + 's ago';
    }

    function setStatus(msg) {
        if (statusEl) statusEl.textContent = msg;
    }

    // ── Auto-refresh timer ───────────────────────────────────────────────────
    function startRefreshTimer() {
        stopRefreshTimer();
        refreshTimer = setInterval(function () {
            // Only refresh when user is logged in (logout div is visible)
            if ($('#divLogout').is(':visible')) {
                refresh();
                lastRefreshTime = Date.now();
                updateStatus();
            }
        }, AUTO_REFRESH_INTERVAL_MS);
    }

    function stopRefreshTimer() {
        if (refreshTimer !== null) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    }

    // ── Auto-claim — step 2: watch #projectDetailTemplate for Assign button ──
    function waitForAssignButton() {
        stopAssignObserver();
        var template = document.getElementById('projectDetailTemplate');
        if (!template) {
            claimInProgress = false;
            return;
        }

        // Check if already present (fast render)
        var assignBtn = template.querySelector('button#assign-indd');
        if (assignBtn) {
            setStatus('Auto-claim: assigning…');
            assignBtn.click();
            claimInProgress = false;
            stopAssignObserver();
            return;
        }

        // Otherwise watch for it to be injected
        assignObserver = new MutationObserver(function () {
            var btn = template.querySelector('button#assign-indd');
            if (btn) {
                stopAssignObserver();
                setStatus('Auto-claim: assigning…');
                btn.click();
                claimInProgress = false;
            }
        });
        assignObserver.observe(template, { childList: true, subtree: true });

        // Safety timeout — if Assign never appears (already assigned), give up
        setTimeout(function () {
            if (assignObserver) {
                stopAssignObserver();
                claimInProgress = false;
                setStatus('Auto-claim: no Assign button found (ad may already be taken)');
            }
        }, 5000);
    }

    function stopAssignObserver() {
        if (assignObserver !== null) {
            assignObserver.disconnect();
            assignObserver = null;
        }
    }

    // ── Auto-claim — step 1: watch queue for new unassigned rows ─────────────
    function startClaimObserver() {
        stopClaimObserver();
        var target = document.querySelector('#tblProjectLinesUnAssigned tbody');
        if (!target) return;

        claimObserver = new MutationObserver(function (mutations) {
            if (claimInProgress) return;

            // Look for a real ad row — it will contain button#open-project
            var viewBtn = document.querySelector('#tblProjectLinesUnAssigned tbody button#open-project');
            if (!viewBtn) return;

            // Extract materialId from onclick="javascript:selectMaterial('...')"
            var onclick = viewBtn.getAttribute('onclick') || '';
            var match = onclick.match(/selectMaterial\('([^']+)'\)/);
            if (!match) return;

            var materialId = match[1];
            claimInProgress = true;
            setStatus('Auto-claim: new ad found — opening detail view…');

            // Call the existing Naviga function to open the detail view
            selectMaterial(materialId);

            // After detail view renders, find and click Assign
            setTimeout(waitForAssignButton, CLAIM_DELAY_MS);
        });

        claimObserver.observe(target, { childList: true, subtree: true });
    }

    function stopClaimObserver() {
        if (claimObserver !== null) {
            claimObserver.disconnect();
            claimObserver = null;
        }
        stopAssignObserver();
        claimInProgress = false;
    }

    // ── UI controls ──────────────────────────────────────────────────────────
    function injectControls() {
        var logoutDiv = document.getElementById('divLogout');
        if (!logoutDiv) return;

        var wrapper = document.createElement('div');
        wrapper.style.cssText = 'margin-top: 6px; font-size: 75%; color: #aaa;';

        // Auto-Refresh checkbox
        var cbRefresh = document.createElement('input');
        cbRefresh.type    = 'checkbox';
        cbRefresh.id      = 'naviga-auto-refresh-toggle';
        cbRefresh.style.cssText = 'vertical-align: middle; margin-right: 4px;';

        var lblRefresh = document.createElement('label');
        lblRefresh.htmlFor   = 'naviga-auto-refresh-toggle';
        lblRefresh.textContent = 'Auto-Refresh';
        lblRefresh.style.cssText = 'margin-right: 10px; cursor: pointer;';

        // Auto-Claim checkbox
        var cbClaim = document.createElement('input');
        cbClaim.type  = 'checkbox';
        cbClaim.id    = 'naviga-auto-claim-toggle';
        cbClaim.style.cssText = 'vertical-align: middle; margin-right: 4px;';

        var lblClaim = document.createElement('label');
        lblClaim.htmlFor   = 'naviga-auto-claim-toggle';
        lblClaim.textContent = 'Auto-Claim';
        lblClaim.style.cssText = 'cursor: pointer;';

        // Status line
        statusEl = document.createElement('div');
        statusEl.style.cssText = 'margin-top: 4px; font-size: 90%; color: #888; font-style: italic;';

        // Wire up events
        cbRefresh.addEventListener('change', function () {
            var settings = loadSettings();
            saveSettings(cbRefresh.checked, settings.autoClaim);
            if (cbRefresh.checked) {
                startRefreshTimer();
            } else {
                stopRefreshTimer();
            }
            updateStatus();
        });

        cbClaim.addEventListener('change', function () {
            var settings = loadSettings();
            saveSettings(settings.autoRefresh, cbClaim.checked);
            if (cbClaim.checked) {
                startClaimObserver();
            } else {
                stopClaimObserver();
            }
        });

        wrapper.appendChild(cbRefresh);
        wrapper.appendChild(lblRefresh);
        wrapper.appendChild(cbClaim);
        wrapper.appendChild(lblClaim);
        wrapper.appendChild(statusEl);
        logoutDiv.appendChild(wrapper);

        // Apply saved settings to checkboxes
        var settings = loadSettings();
        cbRefresh.checked = settings.autoRefresh;
        cbClaim.checked   = settings.autoClaim;
    }

    // ── Entry point ──────────────────────────────────────────────────────────
    function init() {
        injectControls();

        var settings = loadSettings();
        if (settings.autoRefresh) startRefreshTimer();
        if (settings.autoClaim)   startClaimObserver();

        // Update elapsed time display every second
        setInterval(updateStatus, 1000);
    }

    // Wait for the existing index.html inline script to finish setting up
    // (it runs on DOMContentLoaded, so we wait for window load to be safe)
    if (document.readyState === 'complete') {
        init();
    } else {
        window.addEventListener('load', init);
    }
})();
