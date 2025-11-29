/** @odoo-module **/
/**
 * UEIPAB HRMS Dashboard - Payslip Acknowledgment Widget
 *
 * Extends the HrDashboard component to add payslip acknowledgment tracking.
 * Uses Odoo's patch mechanism for clean extension without modifying base module.
 */

import { patch } from "@web/core/utils/patch";
import { HrDashboard } from "@hrms_dashboard/js/hrms_dashboard";
import { useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

patch(HrDashboard.prototype, {
    /**
     * Extend setup to add acknowledgment state and refs
     */
    setup() {
        super.setup(...arguments);

        // Add ref for acknowledgment progress chart
        this.ack_progress_chart = useRef("ack_progress_chart");

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
            }
        } catch (error) {
            console.error('Error fetching payslip acknowledgment stats:', error);
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
