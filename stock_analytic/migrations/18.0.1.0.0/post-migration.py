#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2025 Intresco SAS
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Post-migration script for stock_analytic module.

Unarchives updated views with analytic_distribution.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Unarchive updated views with analytic_distribution.
    
    In Odoo 16.0+, the field analytic_account_id was replaced by
    analytic_distribution across all models including stock.move,
    stock.picking, and stock.move.line.
    
    This script unarchives views with the new field.
    """
    if not version:
        return
    
    _logger.info("=" * 80)
    _logger.info("Unarchiving updated views: analytic_distribution")
    _logger.info("=" * 80)
    
    # Models affected by the analytic_account_id -> analytic_distribution change
    affected_models = (
        'stock.move',
        'stock.picking', 
        'stock.move.line',
        'stock.scrap',
    )
    
    # Unarchive views with new field
    _logger.info("Unarchiving views")
    cr.execute("""
        SELECT id, name, model
        FROM ir_ui_view
        WHERE model IN %s
          AND arch_db::text LIKE '%%analytic_distribution%%'
          AND active = false
    """, (affected_models,))
    
    views_to_unarchive = cr.fetchall()
    
    if not views_to_unarchive:
        _logger.info("✓ No views to unarchive.")
    else:
        _logger.info(f"Found {len(views_to_unarchive)} view(s) to unarchive:")
        for view_id, name, model in views_to_unarchive:
            _logger.info(f"  - ID {view_id}: {name} (model: {model})")
            
            # Unarchive the view
            cr.execute("""
                UPDATE ir_ui_view
                SET active = true
                WHERE id = %s
            """, (view_id,))
        
        _logger.info(f"✓ Unarchived {len(views_to_unarchive)} view(s)")
    
    _logger.info("=" * 80)
    _logger.info("Post-migration completed successfully.")
    _logger.info("=" * 80)