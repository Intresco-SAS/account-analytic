# Copyright 2025 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


def _archive_views(env):
    """Archive views that will be recreated during migration."""
    # Primero verificar qué vistas existen
    env.cr.execute(
        """
        SELECT imd.name, imd.res_id, iv.active, iv.name as view_name
        FROM ir_model_data imd
        JOIN ir_ui_view iv ON imd.res_id = iv.id
        WHERE imd.module = 'product_analytic'
            AND imd.model = 'ir.ui.view'
            AND imd.name IN ('product_normal_form_view', 'view_category_property_form')
        """
    )
    views = env.cr.fetchall()
    _logger.info("=== PRE-MIGRATION product_analytic ===")
    _logger.info("Vistas encontradas: %s", views)
    
    if not views:
        _logger.warning("No se encontraron vistas para archivar!")
        return
    
    # Archivar las vistas
    env.cr.execute(
        """
        UPDATE ir_ui_view
        SET active = False
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'product_analytic'
                AND model = 'ir.ui.view'
                AND name IN ('product_normal_form_view', 'view_category_property_form')
        )
        """
    )
    affected = env.cr.rowcount
    _logger.info("Vistas archivadas: %s", affected)
    
    # Verificar el resultado
    env.cr.execute(
        """
        SELECT imd.name, imd.res_id, iv.active
        FROM ir_model_data imd
        JOIN ir_ui_view iv ON imd.res_id = iv.id
        WHERE imd.module = 'product_analytic'
            AND imd.model = 'ir.ui.view'
            AND imd.name IN ('product_normal_form_view', 'view_category_property_form')
        """
    )
    result = env.cr.fetchall()
    _logger.info("Estado después de archivar: %s", result)


@openupgrade.migrate()
def migrate(env, version):
    _archive_views(env)
