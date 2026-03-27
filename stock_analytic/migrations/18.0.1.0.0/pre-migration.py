#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2025 Intresco SAS
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Pre-migration script for stock_analytic module.

Migrates analytic_account_id to analytic_distribution and archives old views.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migrate analytic_account_id to analytic_distribution and archive old views.
    
    In Odoo 16.0+, the field analytic_account_id was replaced by
    analytic_distribution across all models including stock.move,
    stock.picking, and stock.move.line.
    
    This script migrates the data and archives views with old fields.
    """
    if not version:
        return
    
    _logger.info("=" * 80)
    _logger.info("Migrating analytic_account_id to analytic_distribution")
    _logger.info("=" * 80)
    
    # Models affected by the analytic_account_id -> analytic_distribution change
    affected_models = (
        'stock.move',
        'stock.picking', 
        'stock.move.line',
        'stock.scrap',
    )
    
    # Migrate data for each model
    for model in affected_models:
        table = model.replace('.', '_')
        _logger.info(f"Migrating data for {model} ({table})")
        
        # Check if analytic_distribution exists, if not add it
        cr.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = 'analytic_distribution'
        """, (table,))
        if not cr.fetchone():
            _logger.info(f"  - Adding analytic_distribution column to {table}")
            cr.execute(f"""
                ALTER TABLE {table} ADD COLUMN analytic_distribution jsonb;
            """)
        
        # Migrate: set analytic_distribution = {analytic_account_id: 100.0} where analytic_account_id is not null
        cr.execute(f"""
            UPDATE {table}
            SET analytic_distribution = jsonb_build_object(analytic_account_id::text, 100.0)
            WHERE analytic_account_id IS NOT NULL
              AND (analytic_distribution IS NULL OR analytic_distribution = '{{}}'::jsonb)
        """)
        
        migrated_count = cr.rowcount
        _logger.info(f"  - Migrated {migrated_count} record(s) in {table}")
    
    # Archive views with old fields
    _logger.info("Archiving views with old fields")
    cr.execute("""
        SELECT id, name, model
        FROM ir_ui_view
        WHERE model IN %s
          AND (arch_db::text LIKE '%%analytic_account_id%%' OR arch_db::text LIKE '%%analytic_tag_ids%%')
          AND active = true
    """, (affected_models,))
    
    views_to_archive = cr.fetchall()
    
    if not views_to_archive:
        _logger.info("✓ No views to archive.")
    else:
        _logger.info(f"Found {len(views_to_archive)} view(s) to archive:")
        for view_id, name, model in views_to_archive:
            _logger.info(f"  - ID {view_id}: {name} (model: {model})")
            
            # Archive the view
            cr.execute("""
                UPDATE ir_ui_view
                SET active = false
                WHERE id = %s
            """, (view_id,))
        
        _logger.info(f"✓ Archived {len(views_to_archive)} view(s)")
    
    _logger.info("=" * 80)
    _logger.info("Migration completed successfully.")
    _logger.info("=" * 80)