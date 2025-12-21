/** @odoo-module **/
/**
 * UEIPAB HRMS Dashboard - Payslip Acknowledgment Widget
 *
 * Extends the HrDashboard component to add payslip acknowledgment tracking.
 * Uses Odoo's patch mechanism for clean extension without modifying base module.
 */

import { patch } from "@web/core/utils/patch";
import { HrDashboard } from "@hrms_dashboard/js/hrms_dashboard";
import { onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

console.log("[UEIPAB ACK WIDGET] Module loaded successfully");
console.log("[UEIPAB ACK WIDGET] HrDashboard:", HrDashboard);

patch(HrDashboard.prototype, {
    /**
     * Extend setup to add acknowledgment state
     */
    setup() {
        console.log("[UEIPAB ACK WIDGET] setup() called - patch is working!");
        super.setup(...arguments);

        // Initialize acknowledgment stats in state
        this.state.payslip_ack_stats = {
            is_manager: false,
            personal: {
                total: 0,
                acknowledged: 0,
                pending: 0,
                percentage: 0,
                recent: [],
            },
            batch: {},
        };

        // Fetch acknowledgment data after component starts
        this._fetchAckStats();

        // Render widget after component mounts
        onMounted(() => {
            this._renderAckWidget();
        });
    },

    /**
     * Fetch payslip acknowledgment statistics from backend
     */
    async _fetchAckStats() {
        console.log("[UEIPAB ACK WIDGET] _fetchAckStats() called");
        try {
            const ackStats = await this.orm.call(
                'hr.employee',
                'get_payslip_acknowledgment_stats',
                []
            );
            console.log("[UEIPAB ACK WIDGET] Backend response:", JSON.stringify(ackStats, null, 2));
            console.log("[UEIPAB ACK WIDGET] has_payroll_role:", ackStats.has_payroll_role);
            console.log("[UEIPAB ACK WIDGET] personal.total:", ackStats.personal?.total);
            if (ackStats) {
                this.state.payslip_ack_stats = ackStats;
                // Re-render widget after data is loaded
                this._renderAckWidget();
            }
        } catch (error) {
            console.error('[UEIPAB ACK WIDGET] Error fetching stats:', error);
        }
    },

    /**
     * Render acknowledgment widget into the DOM
     * Adds widget AFTER Announcements and adjusts column sizes via CSS
     */
    _renderAckWidget() {
        console.log("[UEIPAB ACK WIDGET] _renderAckWidget() called");
        const stats = this.state.payslip_ack_stats;
        console.log("[UEIPAB ACK WIDGET] Stats:", stats);

        // Show widget if: user has personal payslips OR is manager with batch data
        const hasPersonalStats = stats && stats.personal && stats.personal.total > 0;
        const hasManagerStats = stats && stats.is_manager && stats.batch && stats.batch.overall && stats.batch.overall.total > 0;

        if (!hasPersonalStats && !hasManagerStats) {
            console.log("[UEIPAB ACK WIDGET] No personal or manager stats, not rendering");
            return;
        }

        // Check if widget already exists
        if (document.querySelector('.payslip_ack_widget')) {
            console.log("[UEIPAB ACK WIDGET] Widget already exists, skipping");
            return;
        }

        // Find the Announcements column
        const headers = document.querySelectorAll('.hr_notification_head');
        console.log("[UEIPAB ACK WIDGET] Found headers:", headers.length);
        let announcementsCol = null;

        for (const header of headers) {
            console.log("[UEIPAB ACK WIDGET] Header text:", header.textContent.trim());
            if (header.textContent.trim() === 'Announcements') {
                announcementsCol = header.closest('.col-md-4, .col-lg-4');
                break;
            }
        }

        if (!announcementsCol) {
            console.log("[UEIPAB ACK WIDGET] Announcements column not found!");
            return;
        }
        console.log("[UEIPAB ACK WIDGET] Found Announcements column, proceeding to render");

        // Adjust Announcements column to be smaller (col-lg-2 instead of col-lg-4)
        announcementsCol.classList.remove('col-lg-4');
        announcementsCol.classList.add('col-lg-2');

        // Determine which view to show:
        // - Managers ALWAYS see Overview (even if they have personal payslips)
        // - Regular employees see Personal view
        const showBatch = hasManagerStats;  // Managers always see overview
        const showPersonal = hasPersonalStats && !hasManagerStats;  // Employees see personal

        let widgetHtml;

        if (showBatch) {
            // Manager view: Show batch/overall stats + personal summary
            const batchStats = stats.batch.overall;
            const pending = batchStats.pending;
            const iconClass = pending > 0 ? 'fa-clock-o' : 'fa-check-circle';
            const statusClass = pending > 0 ? 'ack-status-pending' : 'ack-status-complete';

            // Build personal summary line for managers who have payslips
            let personalSummaryHtml = '';
            if (hasPersonalStats) {
                const myPending = stats.personal.pending;
                const myTotal = stats.personal.total;
                const myAck = stats.personal.acknowledged;
                const myIcon = myPending > 0 ? 'fa-clock-o text-warning' : 'fa-check-circle text-success';
                const myStatus = myPending > 0 ? `${myPending} pending` : 'All done';
                personalSummaryHtml = `
                    <div class="ack-personal-summary" data-action="personal">
                        <i class="fa ${myIcon}"></i>
                        <span>My Status: ${myAck}/${myTotal} ${myPending === 0 ? '✓' : ''}</span>
                    </div>
                `;
            }

            widgetHtml = `
                <div class="col-md-4 col-lg-2 payslip_ack_widget_container">
                    <div class="payslip_ack_widget">
                        <div class="hr_notification_head ${statusClass}">
                            <i class="fa ${iconClass}"></i> Ack Overview
                        </div>
                        <div class="ack-widget-content">
                            <div class="ack-summary-row">
                                <div class="ack-summary-item ack-done" data-action="all_acknowledged">
                                    <div class="ack-summary-count">${batchStats.acknowledged}</div>
                                    <div class="ack-summary-label">Done</div>
                                </div>
                                <div class="ack-summary-item ack-pending-box" data-action="all_pending">
                                    <div class="ack-summary-count">${batchStats.pending}</div>
                                    <div class="ack-summary-label">Pending</div>
                                </div>
                            </div>
                            <div class="ack-progress-section">
                                <div class="ack-progress-track">
                                    <div class="ack-progress-fill" style="width: ${batchStats.percentage}%"></div>
                                </div>
                                <div class="ack-progress-text">${batchStats.percentage}%</div>
                            </div>
                            <div class="ack-batch-info">
                                <small class="text-muted">All batches (${batchStats.total} payslips)</small>
                            </div>
                            ${personalSummaryHtml}
                        </div>
                    </div>
                </div>
            `;
        } else {
            // Personal view: Show employee's own stats
            const pending = stats.personal.pending;
            const iconClass = pending > 0 ? 'fa-clock-o' : 'fa-check-circle';
            const statusClass = pending > 0 ? 'ack-status-pending' : 'ack-status-complete';

            // Build recent payslips HTML (limit to 3 for compact view)
            let recentHtml = '';
            if (stats.personal.recent && stats.personal.recent.length > 0) {
                recentHtml = stats.personal.recent.slice(0, 3).map(slip => `
                    <div class="ack-recent-item ${slip.acknowledged ? 'ack-item-done' : 'ack-item-pending'}">
                        <i class="fa ${slip.acknowledged ? 'fa-check-circle' : 'fa-clock-o'}"></i>
                        <span class="ack-recent-date">${slip.date}</span>
                    </div>
                `).join('');
            }

            widgetHtml = `
                <div class="col-md-4 col-lg-2 payslip_ack_widget_container">
                    <div class="payslip_ack_widget">
                        <div class="hr_notification_head ${statusClass}">
                            <i class="fa ${iconClass}"></i> Payslip Ack
                        </div>
                        <div class="ack-widget-content">
                            <div class="ack-summary-row">
                                <div class="ack-summary-item ack-done" data-action="acknowledged">
                                    <div class="ack-summary-count">${stats.personal.acknowledged}</div>
                                    <div class="ack-summary-label">Done</div>
                                </div>
                                <div class="ack-summary-item ack-pending-box" data-action="pending">
                                    <div class="ack-summary-count">${stats.personal.pending}</div>
                                    <div class="ack-summary-label">Pending</div>
                                </div>
                            </div>
                            <div class="ack-progress-section">
                                <div class="ack-progress-track">
                                    <div class="ack-progress-fill" style="width: ${stats.personal.percentage}%"></div>
                                </div>
                                <div class="ack-progress-text">${stats.personal.percentage}%</div>
                            </div>
                            ${recentHtml ? `
                            <div class="ack-recent-section">
                                <p class="ack-recent-title">Recent</p>
                                ${recentHtml}
                            </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }

        // Insert the widget AFTER the Announcements column
        announcementsCol.insertAdjacentHTML('afterend', widgetHtml);

        // Add click handlers
        const widget = document.querySelector('.payslip_ack_widget');
        if (widget) {
            const pendingBox = widget.querySelector('.ack-pending-box');
            const doneBox = widget.querySelector('.ack-done');

            if (showBatch) {
                // Manager view: click shows all payslips
                if (pendingBox) {
                    pendingBox.addEventListener('click', () => this.view_all_pending_payslips());
                    pendingBox.style.cursor = 'pointer';
                }
                if (doneBox) {
                    doneBox.addEventListener('click', () => this.view_all_acknowledged_payslips());
                    doneBox.style.cursor = 'pointer';
                }
                // Personal summary click - shows manager's own payslips
                const personalSummary = widget.querySelector('.ack-personal-summary');
                if (personalSummary) {
                    personalSummary.addEventListener('click', () => this.view_pending_personal_payslips());
                    personalSummary.style.cursor = 'pointer';
                }
            } else {
                // Personal view: click shows user's payslips
                if (pendingBox) {
                    pendingBox.addEventListener('click', () => this.view_pending_personal_payslips());
                    pendingBox.style.cursor = 'pointer';
                }
                if (doneBox) {
                    doneBox.addEventListener('click', () => this.view_acknowledged_personal_payslips());
                    doneBox.style.cursor = 'pointer';
                }
            }
        }
    },

    /**
     * Navigate to pending personal payslips
     */
    view_pending_personal_payslips() {
        this.action.doAction({
            name: _t("Pending Acknowledgments"),
            type: 'ir.actions.act_window',
            res_model: 'hr.payslip',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['employee_id', '=', this.state.login_employee.id],
                ['is_acknowledged', '=', false],
                ['state', 'in', ['done', 'paid']],
            ],
            target: 'current',
        });
    },

    /**
     * Navigate to acknowledged personal payslips
     */
    view_acknowledged_personal_payslips() {
        this.action.doAction({
            name: _t("Acknowledged Payslips"),
            type: 'ir.actions.act_window',
            res_model: 'hr.payslip',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['employee_id', '=', this.state.login_employee.id],
                ['is_acknowledged', '=', true],
                ['state', 'in', ['done', 'paid']],
            ],
            target: 'current',
        });
    },

    /**
     * Navigate to all pending payslips (manager view)
     */
    view_all_pending_payslips() {
        this.action.doAction({
            name: _t("All Pending Acknowledgments"),
            type: 'ir.actions.act_window',
            res_model: 'hr.payslip',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['is_acknowledged', '=', false],
                ['state', 'in', ['done', 'paid']],
            ],
            target: 'current',
        });
    },

    /**
     * Navigate to all acknowledged payslips (manager view)
     */
    view_all_acknowledged_payslips() {
        this.action.doAction({
            name: _t("All Acknowledged Payslips"),
            type: 'ir.actions.act_window',
            res_model: 'hr.payslip',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['is_acknowledged', '=', true],
                ['state', 'in', ['done', 'paid']],
            ],
            target: 'current',
        });
    },

    /**
     * Navigate to batch pending payslips
     */
    view_batch_pending_payslips(batchId) {
        this.action.doAction({
            name: _t("Batch Pending Acknowledgments"),
            type: 'ir.actions.act_window',
            res_model: 'hr.payslip',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['payslip_run_id', '=', batchId],
                ['is_acknowledged', '=', false],
                ['state', 'in', ['done', 'paid']],
            ],
            target: 'current',
        });
    },

    /**
     * Open specific payslip batch
     */
    open_batch(batchId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'hr.payslip.run',
            res_id: batchId,
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    },

    /**
     * Handle click on latest batch widget
     */
    on_latest_batch_click() {
        const batchStats = this.state.payslip_ack_stats.batch;
        if (batchStats && batchStats.latest_batch && batchStats.latest_batch.id) {
            this.view_batch_pending_payslips(batchStats.latest_batch.id);
        }
    },
});
