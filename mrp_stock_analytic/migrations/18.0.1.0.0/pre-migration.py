#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2025 Intresco SAS
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Pre-migration script for mrp_stock_analytic module.

Migrates analytic data to analytic_distribution in MRP models.
Strategy:
1. If project_id exists with account_id → use project's analytic account
2. If analytic_account_id exists (legacy v15) → convert to distribution
3. Propagate distribution to stock moves
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migrate analytic data to analytic_distribution in MRP context.
    
    Integrates with Odoo's project_id field (v18) while maintaining
    compatibility with legacy analytic_account_id field (v15).
    """
    if not version:
        return
    
    _logger.info("=" * 80)
    _logger.info("Migrating analytic data to analytic_distribution in MRP")
    _logger.info("=" * 80)
    
    table = "mrp_production"
    _logger.info(f"Processing {table}...")
    
    # Check and create analytic_distribution column if needed
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s AND column_name = 'analytic_distribution'
    """, (table,))
    
    if not cr.fetchone():
        _logger.info(f"  - Adding analytic_distribution column to {table}")
        cr.execute(f"ALTER TABLE {table} ADD COLUMN analytic_distribution jsonb;")
    
    # Strategy 1: Migrate from project_id → project.account_id
    # This handles migrations where Odoo Enterprise already created project_id
    _logger.info("  - Strategy 1: Migrating from project_id...")
    cr.execute("""
        UPDATE mrp_production mp
        SET analytic_distribution = jsonb_build_object(pp.account_id::text, 100.0)
        FROM project_project pp
        WHERE mp.project_id = pp.id
          AND pp.account_id IS NOT NULL
          AND (mp.analytic_distribution IS NULL OR mp.analytic_distribution = '{}'::jsonb)
    """)
    project_migrated = cr.rowcount
    _logger.info(f"    ✓ Migrated {project_migrated} record(s) from project_id")
    
    # Strategy 2: Migrate from legacy analytic_account_id (v15)
    # Check if column exists first
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s AND column_name = 'analytic_account_id'
    """, (table,))
    
    if cr.fetchone():
        _logger.info("  - Strategy 2: Migrating from legacy analytic_account_id...")
        cr.execute("""
            UPDATE mrp_production
            SET analytic_distribution = jsonb_build_object(analytic_account_id::text, 100.0)
            WHERE analytic_account_id IS NOT NULL
              AND (analytic_distribution IS NULL OR analytic_distribution = '{}'::jsonb)
        """)
        legacy_migrated = cr.rowcount
        _logger.info(f"    ✓ Migrated {legacy_migrated} record(s) from analytic_account_id")
    else:
        _logger.info("  - Strategy 2: No analytic_account_id column found, skipping")
    
    # Propagate to stock moves (raw materials and finished products)
    _logger.info("  - Propagating analytic_distribution to stock moves...")
    
    # Propagate to raw material moves
    cr.execute("""
        UPDATE stock_move sm
        SET analytic_distribution = mp.analytic_distribution
        FROM mrp_production mp
        WHERE sm.raw_material_production_id = mp.id
          AND mp.analytic_distribution IS NOT NULL
          AND mp.analytic_distribution != '{}'::jsonb
    """)
    raw_moves_updated = cr.rowcount
    _logger.info(f"    ✓ Updated {raw_moves_updated} raw material move(s)")
    
    # Propagate to finished product moves
    cr.execute("""
        UPDATE stock_move sm
        SET analytic_distribution = mp.analytic_distribution
        FROM mrp_production mp
        WHERE sm.production_id = mp.id
          AND mp.analytic_distribution IS NOT NULL
          AND mp.analytic_distribution != '{}'::jsonb
    """)
    finished_moves_updated = cr.rowcount
    _logger.info(f"    ✓ Updated {finished_moves_updated} finished product move(s)")
    
    # Archive views with old fields
    _logger.info("  - Archiving views with legacy analytic fields...")
    cr.execute("""
        SELECT id, name, model
        FROM ir_ui_view
        WHERE model = 'mrp.production'
          AND (arch_db::text LIKE '%%analytic_account_id%%' 
               OR arch_db::text LIKE '%%analytic_tag_ids%%')
          AND active = true
    """)
    
    views_to_archive = cr.fetchall()
    
    if not views_to_archive:
        _logger.info("    ✓ No views to archive")
    else:
        _logger.info(f"    Found {len(views_to_archive)} view(s) to archive:")
        for view_id, name, model in views_to_archive:
            _logger.info(f"      - ID {view_id}: {name}")
            cr.execute("UPDATE ir_ui_view SET active = false WHERE id = %s", (view_id,))
        _logger.info(f"    ✓ Archived {len(views_to_archive)} view(s)")
    
    _logger.info("=" * 80)
    _logger.info("✓ MRP analytic migration completed successfully")
    _logger.info(f"  - From project_id: {project_migrated} productions")
    if cr.execute("""SELECT 1 FROM information_schema.columns 
                     WHERE table_name = 'mrp_production' 
                     AND column_name = 'analytic_account_id'"""):
        _logger.info(f"  - From analytic_account_id: {legacy_migrated} productions")
    _logger.info(f"  - Propagated to {raw_moves_updated} raw + {finished_moves_updated} finished moves")
    _logger.info("=" * 80)
