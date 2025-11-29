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

patch(HrDashboard.prototype, {
    /**
     * Extend setup to add acknowledgment state
     */
    setup() {
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
        try {
            const ackStats = await this.orm.call(
                'hr.employee',
                'get_payslip_acknowledgment_stats',
                []
            );
            if (ackStats) {
                this.state.payslip_ack_stats = ackStats;
                // Re-render widget after data is loaded
                this._renderAckWidget();
            }
        } catch (error) {
            console.error('Error fetching payslip acknowledgment stats:', error);
        }
    },

    /**
     * Render acknowledgment widget into the DOM
     * Adds widget AFTER Announcements and adjusts column sizes via CSS
     */
    _renderAckWidget() {
        const stats = this.state.payslip_ack_stats;
        if (!stats || stats.personal.total === 0) return;

        // Check if widget already exists
        if (document.querySelector('.payslip_ack_widget')) return;

        // Find the Announcements column
        const headers = document.querySelectorAll('.hr_notification_head');
        let announcementsCol = null;

        for (const header of headers) {
            if (header.textContent.trim() === 'Announcements') {
                announcementsCol = header.closest('.col-md-4, .col-lg-4');
                break;
            }
        }

        if (!announcementsCol) return;

        // Adjust Announcements column to be smaller (col-lg-2 instead of col-lg-4)
        announcementsCol.classList.remove('col-lg-4');
        announcementsCol.classList.add('col-lg-2');

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

        // Create the widget as a new column (col-lg-2)
        const widgetHtml = `
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

        // Insert the widget AFTER the Announcements column
        announcementsCol.insertAdjacentHTML('afterend', widgetHtml);

        // Add click handlers
        const widget = document.querySelector('.payslip_ack_widget');
        if (widget) {
            const pendingBox = widget.querySelector('.ack-pending-box');
            const doneBox = widget.querySelector('.ack-done');
            if (pendingBox) {
                pendingBox.addEventListener('click', () => this.view_pending_personal_payslips());
                pendingBox.style.cursor = 'pointer';
            }
            if (doneBox) {
                doneBox.addEventListener('click', () => this.view_acknowledged_personal_payslips());
                doneBox.style.cursor = 'pointer';
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
