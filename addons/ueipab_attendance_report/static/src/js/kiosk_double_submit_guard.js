/** @odoo-module **/

/*
 * Kiosk double-submit guard (UEIPAB)
 * ----------------------------------
 * Odoo's public attendance kiosk guards the BARCODE path (lockScanner + ui.block)
 * but NOT the MANUAL path. `onManualSelection` calls `makeRpcWithGeolocation`,
 * which awaits a slow `getCurrentPosition(enableHighAccuracy)` WITHOUT blocking
 * the UI — so an impatient user taps their name again and fires 2-3 concurrent
 * `manual_selection` RPCs. Those become concurrent UPDATEs on the same
 * hr_attendance row → PostgreSQL "could not serialize access due to concurrent
 * update" errors in the log (non-fatal, but noisy).
 *
 * Fix: mirror the barcode guard on the manual path — a re-entrancy lock plus
 * ui.block() so the screen is busy (and untappable) while the check-in/out RPC
 * (incl. geolocation) is in flight. No core files are modified.
 *
 * See documentation/ATTENDANCE_DANGLING_OPEN_RECORDS.md.
 */

import { patch } from "@web/core/utils/patch";
import publicKioskApp from "@hr_attendance/public_kiosk/public_kiosk_app";

const KioskApp = publicKioskApp.kioskAttendanceApp;

patch(KioskApp.prototype, {
    async onManualSelection(employeeId, enteredPin) {
        if (this._ueipabManualLock) {
            return; // a check-in/out is already in flight — ignore the extra tap
        }
        this._ueipabManualLock = true;
        this.ui.block();
        try {
            return await super.onManualSelection(employeeId, enteredPin);
        } finally {
            this._ueipabManualLock = false;
            this.ui.unblock();
        }
    },

    async kioskConfirm(employeeId) {
        // Guard the name-tap entry point too, so the employee-data fetch can't be
        // fired repeatedly before onManualSelection takes over.
        if (this._ueipabConfirmLock) {
            return;
        }
        this._ueipabConfirmLock = true;
        try {
            return await super.kioskConfirm(employeeId);
        } finally {
            this._ueipabConfirmLock = false;
        }
    },
});
