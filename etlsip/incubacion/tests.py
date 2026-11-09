import sqlite3
from datetime import date, datetime
from decimal import Decimal
from unittest import TestCase
from unittest.mock import DEFAULT, Mock, patch

from incubacion.services import (
    build_prod_huevos_extract_query,
    build_venta_huevo_extract_query,
    delete_costo_prod_detalle_range,
    delete_destination_by_keys,
    delete_incubacion_range,
    delete_ovoscopia_range,
    delete_prod_huevos_range,
    delete_recepcion_range,
    delete_venta_huevo_range,
    delete_venta_pollito_by_keys,
    extract_rows,
    extract_rows_costo_prod_detalle,
    extract_rows_ovoscopia,
    extract_rows_prod_huevos,
    extract_rows_venta_huevo,
    extract_rows_venta_pollito_protein,
    run_etl,
    run_etl_costo_prod_detalle,
    run_etl_ovoscopia,
    run_etl_prod_huevos,
    run_etl_protein_journal,
    run_etl_recepcion,
    run_etl_venta_huevo,
    run_etl_venta_pollito,
    run_etl_venta_pollito_protein,
    transform_presupuesto_rows,
    transform_protein_journal_rows,
)


class VentaPollitoProteinExtractionTests(TestCase):
    def test_trims_text_without_changing_other_values(self):
        columns = [
            "irn", "fecha", "cantidad", "no_incubadora", "granja_lote",
            "cliente", "tipo_documento", "no_ref", "tipo",
        ]
        delivery_date = date(2026, 11, 1)
        quantity = Decimal("12.5")
        cursor = Mock()
        cursor.description = [(column,) for column in columns]
        cursor.fetchall.return_value = [
            (
                123, delivery_date, quantity, "  INC01  ", "\tGRANJA  LOTE\t",
                "\u00a0CLIENTE  UNO\u00a0", None, "   ", "VENTA",
            ),
        ]
        connection = Mock()
        connection.cursor.return_value = cursor

        actual_columns, rows = extract_rows_venta_pollito_protein(
            connection, "dbo.Ventas", delivery_date, date(2026, 11, 9)
        )

        self.assertEqual(actual_columns, columns)
        self.assertEqual(rows, [
            (
                123, delivery_date, quantity, "INC01", "GRANJA  LOTE",
                "CLIENTE  UNO", None, "", "VENTA",
            ),
        ])
        cursor.close.assert_called_once_with()

    def test_empty_extraction_preserves_columns(self):
        cursor = Mock()
        cursor.description = [("irn",), ("cliente",)]
        cursor.fetchall.return_value = []
        connection = Mock()
        connection.cursor.return_value = cursor

        columns, rows = extract_rows_venta_pollito_protein(
            connection, "dbo.Ventas", date(2026, 11, 1), date(2026, 11, 9)
        )

        self.assertEqual(columns, ["irn", "cliente"])
        self.assertEqual(rows, [])
        cursor.close.assert_called_once_with()


class VentaPollitoDeletionTests(TestCase):
    def test_preserves_other_hatcheries_and_unimported_keys(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("CREATE TABLE VentaPollito (irn TEXT, No_incubadora TEXT)")
        connection.executemany("INSERT INTO VentaPollito VALUES (?, ?)", [
            ("A", " INC01 "), ("A", "INC02"), ("A", "INC03"), ("B", "INC01"),
        ])

        deleted = delete_venta_pollito_by_keys(
            connection, "VentaPollito", [("A",)], [" INC01 ", "INC02", "INC01"]
        )

        self.assertEqual(deleted, 2)
        self.assertEqual(
            connection.execute("SELECT * FROM VentaPollito ORDER BY irn").fetchall(),
            [("A", "INC03"), ("B", "INC01")],
        )

    def test_empty_import_or_hatchery_scope_does_not_delete(self):
        for keys, hatcheries in (([], ["INC01"]), ([("A",)], [])):
            with self.subTest(keys=keys, hatcheries=hatcheries):
                connection = Mock()
                self.assertEqual(
                    delete_venta_pollito_by_keys(connection, "VentaPollito", keys, hatcheries),
                    0,
                )
                connection.cursor.assert_not_called()

    def test_missing_hatchery_fails_before_delete(self):
        for value in (None, "", "   ", "\t"):
            with self.subTest(value=value):
                connection = Mock()
                with self.assertRaisesRegex(ValueError, "Missing No_incubadora"):
                    delete_venta_pollito_by_keys(
                        connection, "VentaPollito", [("A",)], ["INC01", value]
                    )
                connection.cursor.assert_not_called()

    def test_legacy_baja_deletion_is_unchanged(self):
        connection = Mock()
        connection.cursor.return_value.rowcount = 1

        self.assertEqual(
            delete_venta_pollito_by_keys(connection, "VentaPollito", [("A",)]), 1
        )

        connection.cursor.return_value.execute.assert_called_once_with(
            "DELETE FROM [VentaPollito] WHERE [irn] = ?", ("A",)
        )

    def test_sales_runners_pass_imported_hatcheries_and_respect_dry_run(self):
        for source in ("excel", "protein"):
            for dry_run in (False, True):
                with self.subTest(source=source, dry_run=dry_run), patch.multiple(
                    "incubacion.services",
                    open_connection=DEFAULT,
                    insert_rows=DEFAULT,
                    delete_venta_pollito_by_keys=DEFAULT,
                    read_venta_pollito_excel=DEFAULT,
                    transform_venta_pollito_rows=DEFAULT,
                    extract_rows_venta_pollito_protein=DEFAULT,
                ) as mocks:
                    config = Mock()
                    columns = ["irn", "No_incubadora" if source == "excel" else "no_incubadora"]
                    rows = [("A", "INC01"), ("B", "INC02")]
                    keys = [("A",), ("B",)]
                    mocks["read_venta_pollito_excel"].return_value = (columns, rows)
                    mocks["transform_venta_pollito_rows"].return_value = (
                        columns, rows, keys, {"source_rows": 2},
                    )
                    mocks["extract_rows_venta_pollito_protein"].return_value = (columns, rows)

                    if source == "excel":
                        run_etl_venta_pollito(config, "ventas.xlsx", dry_run, 1000)
                    else:
                        run_etl_venta_pollito_protein(
                            config, date(2026, 11, 1), date(2026, 11, 9), dry_run, 1000
                        )

                    if dry_run:
                        mocks["delete_venta_pollito_by_keys"].assert_not_called()
                        mocks["insert_rows"].assert_not_called()
                    else:
                        mocks["delete_venta_pollito_by_keys"].assert_called_once_with(
                            mocks["open_connection"].return_value,
                            config.destination_table,
                            keys,
                            hatcheries=["INC01", "INC02"],
                        )


class CostoProdDetalleTests(TestCase):
    def test_extraction_trims_all_text_and_preserves_other_values(self):
        columns = [
            "codigo_generacion", "centro_costo", "no_incubadora", "granja_lote",
            "no_division", "fecha_fin_mes", "er_stage_alloc", "er_compra_unidades",
        ]
        end_date = date(2026, 11, 30)
        amount = Decimal("123.45")
        cursor = Mock()
        cursor.description = [(column,) for column in columns]
        cursor.fetchall.return_value = [
            (" GEN01 ", "\tCC01\t", " INC01 ", "\u00a0LOTE  UNO\u00a0", None, end_date, amount, 10),
        ]
        connection = Mock()
        connection.cursor.return_value = cursor

        actual_columns, rows = extract_rows_costo_prod_detalle(
            connection, "dbo.Origen", date(2026, 11, 9), end_date, ("INC01",), 1, 2
        )

        self.assertEqual(actual_columns, columns)
        self.assertEqual(rows, [("GEN01", "CC01", "INC01", "LOTE  UNO", None, end_date, amount, 10)])
        cursor.close.assert_called_once_with()

    def test_deletion_preserves_other_hatcheries_and_dates_outside_range(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("CREATE TABLE CostoProdDetalle (fecha_fin_mes DATE, no_incubadora TEXT)")
        connection.executemany("INSERT INTO CostoProdDetalle VALUES (?, ?)", [
            ("2026-10-31", "INC01"), ("2026-11-30", " INC01 "),
            ("2026-11-30", "INC02"), ("2026-12-31", "INC02"),
            ("2026-12-31", "INC03"), ("2027-01-31", "INC01"),
        ])

        with patch.dict(sqlite3.adapters, {(date, sqlite3.PrepareProtocol): date.isoformat}):
            deleted = delete_costo_prod_detalle_range(
                connection, "CostoProdDetalle", "fecha_fin_mes",
                date(2026, 11, 30), date(2026, 12, 31), [" INC01 ", "INC02", "INC01"],
            )

        self.assertEqual(deleted, 3)
        self.assertEqual(
            connection.execute("SELECT * FROM CostoProdDetalle ORDER BY fecha_fin_mes").fetchall(),
            [("2026-10-31", "INC01"), ("2026-12-31", "INC03"), ("2027-01-31", "INC01")],
        )

    def test_empty_hatchery_scope_does_not_delete(self):
        connection = Mock()
        self.assertEqual(delete_costo_prod_detalle_range(
            connection, "dbo.CostoProdDetalle", "fecha_fin_mes",
            date(2026, 11, 30), date(2026, 12, 31), [],
        ), 0)
        connection.cursor.assert_not_called()

    def test_invalid_hatchery_fails_before_any_delete(self):
        for value in (None, "", "   ", "\t"):
            with self.subTest(value=value):
                connection = Mock()
                with self.assertRaisesRegex(ValueError, "Missing no_incubadora"):
                    delete_costo_prod_detalle_range(
                        connection, "dbo.CostoProdDetalle", "fecha_fin_mes",
                        date(2026, 11, 30), date(2026, 12, 31), ["INC01", value],
                    )
                connection.cursor.assert_not_called()

    def test_runner_uses_actual_hatcheries_and_skips_empty_or_dry_run(self):
        for rows, dry_run in (([("INC01",)], False), ([], False), ([("INC01",)], True)):
            with self.subTest(rows=rows, dry_run=dry_run), patch.multiple(
                "incubacion.services", open_connection=DEFAULT,
                extract_rows_costo_prod_detalle=DEFAULT,
                delete_costo_prod_detalle_range=DEFAULT, insert_rows=DEFAULT,
            ) as mocks:
                config = Mock()
                config.hatcheries = ("INC01", "INC02")
                config.destination_date_column = "fecha_fin_mes"
                mocks["extract_rows_costo_prod_detalle"].return_value = (["no_incubadora"], rows)
                mocks["delete_costo_prod_detalle_range"].return_value = 2
                mocks["insert_rows"].return_value = len(rows)

                result = run_etl_costo_prod_detalle(
                    config, date(2026, 11, 9), date(2026, 12, 9), dry_run, 1000
                )

                if dry_run or not rows:
                    mocks["delete_costo_prod_detalle_range"].assert_not_called()
                    mocks["insert_rows"].assert_not_called()
                    self.assertEqual(result, {"source_rows": len(rows), "deleted_rows": 0, "inserted_rows": 0})
                else:
                    mocks["delete_costo_prod_detalle_range"].assert_called_once_with(
                        destination_conn=mocks["open_connection"].return_value,
                        destination_table=config.destination_table,
                        destination_date_column="fecha_fin_mes",
                        start_date=date(2026, 11, 30), end_date=date(2026, 12, 31),
                        hatcheries=["INC01"],
                    )
                    self.assertEqual(result, {"source_rows": 1, "deleted_rows": 2, "inserted_rows": 1})
                    mocks["open_connection"].return_value.commit.assert_called_once_with()

    def test_insert_failure_rolls_back_deletion(self):
        with patch.multiple(
            "incubacion.services", open_connection=DEFAULT,
            extract_rows_costo_prod_detalle=DEFAULT,
            delete_costo_prod_detalle_range=DEFAULT, insert_rows=DEFAULT,
        ) as mocks:
            source = Mock()
            destination = Mock()
            mocks["open_connection"].side_effect = [source, destination]
            mocks["extract_rows_costo_prod_detalle"].return_value = (["no_incubadora"], [("INC01",)])
            mocks["insert_rows"].side_effect = RuntimeError("Insert failed")

            with self.assertRaisesRegex(RuntimeError, "Insert failed"):
                run_etl_costo_prod_detalle(
                    Mock(), date(2026, 11, 9), date(2026, 12, 9), False, 1000
                )

            destination.rollback.assert_called_once_with()
            destination.commit.assert_not_called()
            source.close.assert_called_once_with()
            destination.close.assert_called_once_with()


class IncubacionTests(TestCase):
    def test_extraction_trims_text_and_preserves_values(self):
        columns = ["grupo_ubicacion", "granja_lote", "xDate", "cantidad_relativa", "elemento_costo"]
        start_date = date(2026, 11, 1)
        amount = Decimal("12.50")
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.description = [(column,) for column in columns]
        cursor.fetchall.return_value = [(" HAT INC01 ", "\tLOTE  UNO\u00a0", start_date, amount, None)]

        actual_columns, rows = extract_rows(
            connection, "dbo.Origen", start_date, date(2026, 11, 9), ("SOURCE",)
        )

        self.assertEqual(actual_columns, columns)
        self.assertEqual(rows, [("HAT INC01", "LOTE  UNO", start_date, amount, None)])
        cursor.close.assert_called_once_with()

    def test_deletion_preserves_other_groups_and_dates(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("CREATE TABLE Incubacion (xDate DATE, grupo_costo TEXT)")
        connection.executemany("INSERT INTO Incubacion VALUES (?, ?)", [
            ("2026-10-31", "HAT INC01"), ("2026-11-01", " HAT INC01 "),
            ("2026-11-09", "HAT INC02"), ("2026-11-09", "HAT INC03"),
            ("2026-11-10", "HAT INC01"),
        ])

        with patch.dict(sqlite3.adapters, {(date, sqlite3.PrepareProtocol): date.isoformat}):
            deleted = delete_incubacion_range(
                connection, "Incubacion", "xDate", date(2026, 11, 1), date(2026, 11, 9),
                [" HAT INC01 ", "HAT INC02", "HAT INC01"],
            )

        self.assertEqual(deleted, 2)
        self.assertEqual(connection.execute("SELECT * FROM Incubacion ORDER BY xDate").fetchall(), [
            ("2026-10-31", "HAT INC01"), ("2026-11-09", "HAT INC03"),
            ("2026-11-10", "HAT INC01"),
        ])

    def test_empty_group_scope_never_deletes(self):
        connection = Mock()
        self.assertEqual(delete_incubacion_range(
            connection, "dbo.Incubacion", "xDate", date(2026, 11, 1), date(2026, 11, 9), [],
        ), 0)
        connection.cursor.assert_not_called()

    def test_invalid_group_fails_before_delete(self):
        for value in (None, "", "   ", "\t"):
            with self.subTest(value=value):
                connection = Mock()
                with self.assertRaisesRegex(ValueError, "Missing grupo_ubicacion"):
                    delete_incubacion_range(
                        connection, "dbo.Incubacion", "xDate",
                        date(2026, 11, 1), date(2026, 11, 9), ["HAT INC01", value],
                    )
                connection.cursor.assert_not_called()

    def test_command_service_scopes_deletion_and_skips_empty_or_dry_run(self):
        for rows, dry_run in (([("HAT INC01",)], False), ([], False), ([("HAT INC01",)], True)):
            with self.subTest(rows=rows, dry_run=dry_run), patch.multiple(
                "incubacion.services", open_connection=DEFAULT, extract_rows=DEFAULT,
                delete_incubacion_range=DEFAULT, delete_destination_range=DEFAULT, insert_rows=DEFAULT,
            ) as mocks:
                mocks["extract_rows"].return_value = (["grupo_ubicacion"], rows)
                mocks["delete_incubacion_range"].return_value = 2
                mocks["insert_rows"].return_value = len(rows)
                config = Mock()

                result = run_etl(config, date(2026, 11, 1), date(2026, 11, 9), dry_run, 1000)

                mocks["delete_destination_range"].assert_not_called()
                if dry_run or not rows:
                    mocks["delete_incubacion_range"].assert_not_called()
                    mocks["insert_rows"].assert_not_called()
                    self.assertEqual(result, {"source_rows": len(rows), "deleted_rows": 0, "inserted_rows": 0})
                else:
                    mocks["delete_incubacion_range"].assert_called_once_with(
                        destination_conn=mocks["open_connection"].return_value,
                        destination_table=config.destination_table,
                        destination_date_column=config.destination_date_column,
                        start_date=date(2026, 11, 1), end_date=date(2026, 11, 9),
                        location_groups=["HAT INC01"],
                    )
                    self.assertEqual(result, {"source_rows": 1, "deleted_rows": 2, "inserted_rows": 1})

    def test_insert_failure_rolls_back_deletion(self):
        with patch.multiple(
            "incubacion.services", open_connection=DEFAULT, extract_rows=DEFAULT,
            delete_incubacion_range=DEFAULT, insert_rows=DEFAULT,
        ) as mocks:
            source = Mock()
            destination = Mock()
            mocks["open_connection"].side_effect = [source, destination]
            mocks["extract_rows"].return_value = (["grupo_ubicacion"], [("HAT INC01",)])
            mocks["insert_rows"].side_effect = RuntimeError("Insert failed")

            with self.assertRaisesRegex(RuntimeError, "Insert failed"):
                run_etl(Mock(), date(2026, 11, 1), date(2026, 11, 9), False, 1000)

            destination.rollback.assert_called_once_with()
            destination.commit.assert_not_called()
            source.close.assert_called_once_with()
            destination.close.assert_called_once_with()


class VentaHuevoTests(TestCase):
    def setUp(self):
        self.start_date = date(2026, 11, 1)
        self.end_date = date(2026, 11, 9)
        self.columns = [
            "fecha", "no_granja", "granja_lote", "cliente", "sku",
            "huevos", "irn", "fecha_semana", "no_ref",
        ]
        self.source_row = (
            datetime(2026, 11, 9, 23, 59), " 00123 ", "\t00123-00456\u00a0",
            " CLIENTE  UNO ", " SKU01 ", Decimal("100.5"), " IRN01 ", self.start_date, None,
        )

    def test_query_trims_codes_and_uses_exclusive_end_date(self):
        query = build_venta_huevo_extract_query("dbo.Origen")

        self.assertIn(
            "LEFT(LTRIM(RTRIM(ComplexEntityNo)), LEN(LTRIM(RTRIM(ComplexEntityNo))) - 5) AS no_granja",
            query,
        )
        self.assertIn("LTRIM(RTRIM(ComplexEntityNo)) AS granja_lote", query)
        self.assertIn("LTRIM(RTRIM(BillToCustomerNo)) AS cliente", query)
        self.assertIn("LTRIM(RTRIM(SalesSKUNo)) AS sku", query)
        self.assertIn("DeliveryDate >= ? AND DeliveryDate < ?", query)

    def test_extraction_trims_codes_and_preserves_other_values(self):
        source = Mock()
        cursor = source.cursor.return_value
        cursor.description = [(column,) for column in self.columns]
        cursor.fetchall.return_value = [self.source_row]

        columns, rows = extract_rows_venta_huevo(source, "dbo.Origen", self.start_date, self.end_date)

        self.assertEqual(columns, self.columns)
        self.assertEqual(rows, [
            (datetime(2026, 11, 9, 23, 59), "00123", "00123-00456", "CLIENTE  UNO",
             "SKU01", Decimal("100.5"), "IRN01", self.start_date, None),
        ])
        self.assertEqual(cursor.execute.call_args.args[1], [self.start_date, date(2026, 11, 10)])
        cursor.close.assert_called_once_with()

    def test_invalid_codes_fail_before_writes_in_real_and_dry_runs(self):
        for column in ("no_granja", "granja_lote", "cliente", "sku", "irn"):
            for blank in (None, "", "   ", "\t\u00a0"):
                for dry_run in (False, True):
                    with self.subTest(column=column, blank=blank, dry_run=dry_run):
                        source = Mock()
                        destination = Mock()
                        row = list(self.source_row)
                        row[self.columns.index(column)] = blank
                        source.cursor.return_value.description = [(name,) for name in self.columns]
                        source.cursor.return_value.fetchall.return_value = [tuple(row)]
                        config = Mock(source_table="dbo.Origen", destination_table="dbo.VentaHuevo")

                        with patch("incubacion.services.open_connection", side_effect=[source, destination]):
                            with self.assertRaisesRegex(ValueError, f"missing required value for {column}"):
                                run_etl_venta_huevo(config, self.start_date, self.end_date, dry_run, 1000)

                        destination.cursor.assert_not_called()
                        destination.commit.assert_not_called()
                        source.cursor.return_value.close.assert_called_once_with()

    def test_deletion_preserves_other_farms_and_includes_entire_final_day(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("CREATE TABLE VentaHuevo (fecha TEXT, no_granja TEXT)")
        connection.executemany("INSERT INTO VentaHuevo VALUES (?, ?)", [
            ("2026-10-31 23:59:59", "GRANJA01"), ("2026-11-01 00:00:00", " GRANJA01 "),
            ("2026-11-09 23:59:59", "GRANJA01"), ("2026-11-09 12:00:00", "GRANJA02"),
            ("2026-11-09 12:00:00", "GRANJA03"), ("2026-11-10 00:00:00", "GRANJA01"),
        ])
        adapters = {
            (date, sqlite3.PrepareProtocol):
                lambda value: datetime.combine(value, datetime.min.time()).isoformat(" "),
        }

        with patch.dict(sqlite3.adapters, adapters):
            deleted = delete_venta_huevo_range(
                connection, "VentaHuevo", "fecha", self.start_date, self.end_date,
                [" GRANJA01 ", "GRANJA02", "GRANJA01"],
            )

        self.assertEqual(deleted, 3)
        self.assertEqual(connection.execute("SELECT * FROM VentaHuevo ORDER BY fecha").fetchall(), [
            ("2026-10-31 23:59:59", "GRANJA01"), ("2026-11-09 12:00:00", "GRANJA03"),
            ("2026-11-10 00:00:00", "GRANJA01"),
        ])

    def test_empty_or_invalid_farm_scope_never_deletes(self):
        for farms in ([], ["GRANJA01", None], ["GRANJA01", ""], ["GRANJA01", "\t\u00a0"]):
            with self.subTest(farms=farms):
                connection = Mock()
                if farms:
                    with self.assertRaisesRegex(ValueError, "Missing no_granja"):
                        delete_venta_huevo_range(
                            connection, "dbo.VentaHuevo", "fecha", self.start_date, self.end_date, farms
                        )
                else:
                    self.assertEqual(delete_venta_huevo_range(
                        connection, "dbo.VentaHuevo", "fecha", self.start_date, self.end_date, farms
                    ), 0)
                connection.cursor.assert_not_called()

    def test_command_and_dashboard_scope_deletion_and_skip_empty_or_dry_run(self):
        from incubacion.views import _run_etl_with_progress

        for route in ("command", "dashboard"):
            for rows, dry_run in (([("GRANJA01",), ("GRANJA02",)], False), ([], False), ([("GRANJA01",)], True)):
                with self.subTest(route=route, rows=rows, dry_run=dry_run), patch.multiple(
                    "incubacion.services", open_connection=DEFAULT, extract_rows_venta_huevo=DEFAULT,
                    delete_venta_huevo_range=DEFAULT, delete_destination_range=DEFAULT, insert_rows=DEFAULT,
                ) as mocks:
                    config = Mock()
                    mocks["extract_rows_venta_huevo"].return_value = (["no_granja"], rows)
                    mocks["delete_venta_huevo_range"].return_value = 3
                    mocks["insert_rows"].return_value = len(rows)

                    if route == "command":
                        result = run_etl_venta_huevo(config, self.start_date, self.end_date, dry_run, 1000)
                    else:
                        result = _run_etl_with_progress(
                            "venta_huevo", config, None, self.start_date, self.end_date,
                            dry_run, 1000, Mock(),
                        )

                    mocks["delete_destination_range"].assert_not_called()
                    if dry_run or not rows:
                        mocks["delete_venta_huevo_range"].assert_not_called()
                        mocks["insert_rows"].assert_not_called()
                        self.assertEqual(result["deleted_rows"], 0)
                        self.assertEqual(result["inserted_rows"], 0)
                    else:
                        mocks["delete_venta_huevo_range"].assert_called_once_with(
                            destination_conn=mocks["open_connection"].return_value,
                            destination_table=config.destination_table,
                            destination_date_column=config.destination_date_column,
                            start_date=self.start_date, end_date=self.end_date,
                            farms=["GRANJA01", "GRANJA02"],
                        )
                        self.assertEqual(result["deleted_rows"], 3)
                        self.assertEqual(result["inserted_rows"], 2)

    def test_insert_failure_rolls_back_deletion(self):
        with patch.multiple(
            "incubacion.services", open_connection=DEFAULT, extract_rows_venta_huevo=DEFAULT,
            delete_venta_huevo_range=DEFAULT, insert_rows=DEFAULT,
        ) as mocks:
            source = Mock()
            destination = Mock()
            mocks["open_connection"].side_effect = [source, destination]
            mocks["extract_rows_venta_huevo"].return_value = (["no_granja"], [("GRANJA01",)])
            mocks["insert_rows"].side_effect = RuntimeError("Insert failed")

            with self.assertRaisesRegex(RuntimeError, "Insert failed"):
                run_etl_venta_huevo(Mock(), self.start_date, self.end_date, False, 1000)

            destination.rollback.assert_called_once_with()
            destination.commit.assert_not_called()
            source.close.assert_called_once_with()
            destination.close.assert_called_once_with()


class OvoscopiaTests(TestCase):
    def setUp(self):
        self.start_date = date(2026, 11, 1)
        self.end_date = date(2026, 11, 9)

    def test_extraction_trims_text_and_uses_exclusive_end_date(self):
        columns = ["No_incubadora", "No_granja", "No_lote", "No_carga", "Fecha_nacimiento", "Huevos_muestra"]
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.description = [(column,) for column in columns]
        cursor.fetchall.return_value = [
            (" INC01 ", "\tGRANJA  UNO\u00a0", " LOTE01 ", None, self.end_date, Decimal("100.5")),
        ]

        actual_columns, rows = extract_rows_ovoscopia(connection, self.start_date, self.end_date)

        self.assertEqual(actual_columns, columns)
        self.assertEqual(rows, [
            ("INC01", "GRANJA  UNO", "LOTE01", None, self.end_date, Decimal("100.5")),
        ])
        self.assertEqual(cursor.execute.call_args.args[1:], (self.start_date, date(2026, 11, 10)))
        cursor.close.assert_called_once_with()

    def test_deletion_scopes_hatcheries_and_includes_entire_final_day(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("CREATE TABLE Ovoscopia (Fecha_nacimiento TEXT, No_incubadora TEXT)")
        connection.executemany("INSERT INTO Ovoscopia VALUES (?, ?)", [
            ("2026-10-31 23:59:59", "INC01"), ("2026-11-01 00:00:00", " INC01 "),
            ("2026-11-09 23:59:59", "INC01"), ("2026-11-09 12:00:00", "INC02"),
            ("2026-11-09 12:00:00", "INC03"), ("2026-11-10 00:00:00", "INC01"),
        ])
        adapters = {
            (date, sqlite3.PrepareProtocol):
                lambda value: datetime.combine(value, datetime.min.time()).isoformat(" "),
        }

        with patch.dict(sqlite3.adapters, adapters):
            deleted = delete_ovoscopia_range(
                connection, "Ovoscopia", self.start_date, self.end_date,
                [" INC01 ", "INC02", "INC01"],
            )

        self.assertEqual(deleted, 3)
        self.assertEqual(connection.execute("SELECT * FROM Ovoscopia ORDER BY Fecha_nacimiento").fetchall(), [
            ("2026-10-31 23:59:59", "INC01"), ("2026-11-09 12:00:00", "INC03"),
            ("2026-11-10 00:00:00", "INC01"),
        ])

    def test_empty_hatchery_scope_never_deletes(self):
        connection = Mock()

        self.assertEqual(delete_ovoscopia_range(
            connection, "dbo.Ovoscopia", self.start_date, self.end_date, [],
        ), 0)

        connection.cursor.assert_not_called()

    def test_missing_hatchery_fails_before_any_delete(self):
        for value in (None, "", "   ", "\t\u00a0"):
            with self.subTest(value=value):
                connection = Mock()
                with self.assertRaisesRegex(ValueError, "Missing No_incubadora"):
                    delete_ovoscopia_range(
                        connection, "dbo.Ovoscopia", self.start_date, self.end_date, ["INC01", value]
                    )
                connection.cursor.assert_not_called()

    def test_command_and_dashboard_scope_deletion_and_skip_empty_or_dry_run(self):
        from incubacion.views import _run_etl_with_progress

        for route in ("command", "dashboard"):
            for rows, dry_run in (([("INC01",), ("INC02",)], False), ([], False), ([("INC01",)], True)):
                with self.subTest(route=route, rows=rows, dry_run=dry_run), patch.multiple(
                    "incubacion.services", open_connection=DEFAULT, extract_rows_ovoscopia=DEFAULT,
                    delete_ovoscopia_range=DEFAULT, delete_destination_range=DEFAULT, insert_rows=DEFAULT,
                ) as mocks:
                    config = Mock()
                    mocks["extract_rows_ovoscopia"].return_value = (["No_incubadora"], rows)
                    mocks["delete_ovoscopia_range"].return_value = 3
                    mocks["insert_rows"].return_value = len(rows)

                    if route == "command":
                        result = run_etl_ovoscopia(config, self.start_date, self.end_date, dry_run, 1000)
                    else:
                        result = _run_etl_with_progress(
                            "ovoscopia", config, None, self.start_date, self.end_date,
                            dry_run, 1000, Mock(),
                        )

                    mocks["delete_destination_range"].assert_not_called()
                    if dry_run or not rows:
                        mocks["delete_ovoscopia_range"].assert_not_called()
                        mocks["insert_rows"].assert_not_called()
                        self.assertEqual(result["deleted_rows"], 0)
                        self.assertEqual(result["inserted_rows"], 0)
                    else:
                        mocks["delete_ovoscopia_range"].assert_called_once_with(
                            mocks["open_connection"].return_value, config.destination_table,
                            self.start_date, self.end_date, hatcheries=["INC01", "INC02"],
                        )
                        mocks["insert_rows"].assert_called_once_with(
                            mocks["open_connection"].return_value, config.destination_table,
                            ["No_incubadora"], rows, 1000, fast_executemany=False,
                        )
                        self.assertEqual(result["deleted_rows"], 3)
                        self.assertEqual(result["inserted_rows"], 2)

    def test_insert_failure_rolls_back_deletion(self):
        with patch.multiple(
            "incubacion.services", open_connection=DEFAULT, extract_rows_ovoscopia=DEFAULT,
            delete_ovoscopia_range=DEFAULT, insert_rows=DEFAULT,
        ) as mocks:
            source = Mock()
            destination = Mock()
            mocks["open_connection"].side_effect = [source, destination]
            mocks["extract_rows_ovoscopia"].return_value = (["No_incubadora"], [("INC01",)])
            mocks["insert_rows"].side_effect = RuntimeError("Insert failed")

            with self.assertRaisesRegex(RuntimeError, "Insert failed"):
                run_etl_ovoscopia(Mock(), self.start_date, self.end_date, False, 1000)

            destination.rollback.assert_called_once_with()
            destination.commit.assert_not_called()
            source.close.assert_called_once_with()
            destination.close.assert_called_once_with()


class ProdHuevosTests(TestCase):
    def setUp(self):
        self.start_date = date(2026, 11, 1)
        self.end_date = date(2026, 11, 9)

    def test_query_trims_farm_and_entity_before_concatenation(self):
        query = build_prod_huevos_extract_query("dbo.Origen")

        self.assertIn("LTRIM(RTRIM(FarmNo)) AS No_granja", query)
        self.assertIn(
            "LTRIM(RTRIM(FarmNo)) + '-' + LTRIM(RTRIM(EntityNo)) AS Granja_lote", query
        )

    def test_extraction_trims_text_and_preserves_other_values(self):
        columns = ["No_granja", "Granja_lote", "fecha", "HI", "irn"]
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.description = [(column,) for column in columns]
        cursor.fetchall.return_value = [
            (" 00123 ", "\t00123-LOTE  UNO\u00a0", self.start_date, Decimal("100.5"), None),
        ]

        actual_columns, rows = extract_rows_prod_huevos(
            connection, "dbo.Origen", self.start_date, self.end_date
        )

        self.assertEqual(actual_columns, columns)
        self.assertEqual(rows, [
            ("00123", "00123-LOTE  UNO", self.start_date, Decimal("100.5"), None),
        ])
        cursor.close.assert_called_once_with()

    def test_deletion_preserves_other_farms_and_dates(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("CREATE TABLE ProdHuevos (Fecha DATE, No_granja TEXT)")
        connection.executemany("INSERT INTO ProdHuevos VALUES (?, ?)", [
            ("2026-10-31", "GRANJA01"), ("2026-11-01", " GRANJA01 "),
            ("2026-11-09", "GRANJA02"), ("2026-11-09", "GRANJA03"),
            ("2026-11-10", "GRANJA02"),
        ])

        with patch.dict(sqlite3.adapters, {(date, sqlite3.PrepareProtocol): date.isoformat}):
            deleted = delete_prod_huevos_range(
                connection, "ProdHuevos", "Fecha", self.start_date, self.end_date,
                [" GRANJA01 ", "GRANJA02", "GRANJA01"],
            )

        self.assertEqual(deleted, 2)
        self.assertEqual(connection.execute("SELECT * FROM ProdHuevos ORDER BY Fecha").fetchall(), [
            ("2026-10-31", "GRANJA01"), ("2026-11-09", "GRANJA03"), ("2026-11-10", "GRANJA02"),
        ])

    def test_empty_or_invalid_farms_execute_no_delete(self):
        for farms in ([], ["GRANJA01", None], ["GRANJA01", ""], ["GRANJA01", "\t\u00a0"]):
            with self.subTest(farms=farms):
                connection = Mock()
                if farms:
                    with self.assertRaisesRegex(ValueError, "Missing No_granja"):
                        delete_prod_huevos_range(
                            connection, "dbo.ProdHuevos", "Fecha", self.start_date, self.end_date, farms
                        )
                else:
                    self.assertEqual(delete_prod_huevos_range(
                        connection, "dbo.ProdHuevos", "Fecha", self.start_date, self.end_date, farms
                    ), 0)
                connection.cursor.assert_not_called()

    def test_command_and_dashboard_scope_deletion_and_skip_empty_or_dry_run(self):
        from incubacion.views import _run_etl_with_progress

        for route in ("command", "dashboard"):
            for rows, dry_run in (([("GRANJA01",), ("GRANJA02",)], False), ([], False), ([("GRANJA01",)], True)):
                with self.subTest(route=route, rows=rows, dry_run=dry_run), patch.multiple(
                    "incubacion.services", open_connection=DEFAULT, extract_rows_prod_huevos=DEFAULT,
                    delete_prod_huevos_range=DEFAULT, delete_destination_range=DEFAULT, insert_rows=DEFAULT,
                ) as mocks:
                    config = Mock()
                    mocks["extract_rows_prod_huevos"].return_value = (["No_granja"], rows)
                    mocks["delete_prod_huevos_range"].return_value = 3
                    mocks["insert_rows"].return_value = len(rows)

                    if route == "command":
                        result = run_etl_prod_huevos(config, self.start_date, self.end_date, dry_run, 1000)
                    else:
                        result = _run_etl_with_progress(
                            "prod_huevos", config, None, self.start_date, self.end_date,
                            dry_run, 1000, Mock(),
                        )

                    mocks["delete_destination_range"].assert_not_called()
                    if dry_run or not rows:
                        mocks["delete_prod_huevos_range"].assert_not_called()
                        mocks["insert_rows"].assert_not_called()
                        self.assertEqual(result["deleted_rows"], 0)
                        self.assertEqual(result["inserted_rows"], 0)
                    else:
                        mocks["delete_prod_huevos_range"].assert_called_once_with(
                            destination_conn=mocks["open_connection"].return_value,
                            destination_table=config.destination_table,
                            destination_date_column=config.destination_date_column,
                            start_date=self.start_date, end_date=self.end_date,
                            farms=["GRANJA01", "GRANJA02"],
                        )
                        self.assertEqual(result["deleted_rows"], 3)
                        self.assertEqual(result["inserted_rows"], 2)

    def test_insert_failure_rolls_back_deletion(self):
        with patch.multiple(
            "incubacion.services", open_connection=DEFAULT, extract_rows_prod_huevos=DEFAULT,
            delete_prod_huevos_range=DEFAULT, insert_rows=DEFAULT,
        ) as mocks:
            source = Mock()
            destination = Mock()
            mocks["open_connection"].side_effect = [source, destination]
            mocks["extract_rows_prod_huevos"].return_value = (["No_granja"], [("GRANJA01",)])
            mocks["insert_rows"].side_effect = RuntimeError("Insert failed")

            with self.assertRaisesRegex(RuntimeError, "Insert failed"):
                run_etl_prod_huevos(Mock(), self.start_date, self.end_date, False, 1000)

            destination.rollback.assert_called_once_with()
            destination.commit.assert_not_called()
            source.close.assert_called_once_with()
            destination.close.assert_called_once_with()


class RecepcionDeletionTests(TestCase):
    def setUp(self):
        self.start_date = date(2026, 11, 1)
        self.end_date = date(2026, 11, 9)

    def test_deletion_preserves_unimported_hatcheries_and_other_dates(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("CREATE TABLE Recepcion (Fecha_envio DATE, No_incubadora TEXT)")
        connection.executemany("INSERT INTO Recepcion VALUES (?, ?)", [
            ("2026-10-31", "INC01"), ("2026-11-01", " INC01 "),
            ("2026-11-09", "INC02"), ("2026-11-09", "INC03"),
            ("2026-11-10", "INC02"),
        ])

        with patch.dict(sqlite3.adapters, {(date, sqlite3.PrepareProtocol): date.isoformat}):
            deleted = delete_recepcion_range(
                connection, "Recepcion", "Fecha_envio", self.start_date, self.end_date,
                [" INC01 ", "INC02", "INC01"],
            )

        self.assertEqual(deleted, 2)
        self.assertEqual(connection.execute("SELECT * FROM Recepcion ORDER BY Fecha_envio").fetchall(), [
            ("2026-10-31", "INC01"), ("2026-11-09", "INC03"), ("2026-11-10", "INC02"),
        ])

    def test_empty_hatchery_scope_does_not_execute_delete(self):
        connection = Mock()
        self.assertEqual(delete_recepcion_range(
            connection, "dbo.Recepcion", "Fecha_envio", self.start_date, self.end_date, [],
        ), 0)
        connection.cursor.assert_not_called()

    def test_missing_hatchery_fails_before_any_delete(self):
        for value in (None, "", "   ", "\t\u00a0"):
            with self.subTest(value=value):
                connection = Mock()
                with self.assertRaisesRegex(ValueError, "Missing No_incubadora"):
                    delete_recepcion_range(
                        connection, "dbo.Recepcion", "Fecha_envio", self.start_date, self.end_date,
                        ["INC01", value],
                    )
                connection.cursor.assert_not_called()

    def test_command_and_dashboard_scope_deletion_and_skip_empty_or_dry_run(self):
        from incubacion.views import _run_etl_with_progress

        for route in ("command", "dashboard"):
            for rows, dry_run in (([(" INC01 ",), ("INC02",)], False), ([], False), ([("INC01",)], True)):
                with self.subTest(route=route, rows=rows, dry_run=dry_run), patch.multiple(
                    "incubacion.services", open_connection=DEFAULT, extract_rows_recepcion=DEFAULT,
                    delete_recepcion_range=DEFAULT, delete_destination_range=DEFAULT,
                    insert_rows_recepcion=DEFAULT, calculate_data_summary=DEFAULT,
                ) as mocks:
                    config = Mock()
                    mocks["extract_rows_recepcion"].return_value = (["No_incubadora"], rows)
                    mocks["delete_recepcion_range"].return_value = 3
                    mocks["insert_rows_recepcion"].return_value = len(rows)
                    mocks["calculate_data_summary"].return_value = {}

                    if route == "command":
                        result = run_etl_recepcion(
                            config, self.start_date, self.end_date, dry_run, 1000
                        )
                    else:
                        result = _run_etl_with_progress(
                            "recepcion", config, None, self.start_date, self.end_date,
                            dry_run, 1000, Mock(),
                        )

                    mocks["delete_destination_range"].assert_not_called()
                    if dry_run or not rows:
                        mocks["delete_recepcion_range"].assert_not_called()
                        mocks["insert_rows_recepcion"].assert_not_called()
                        self.assertEqual(result["deleted_rows"], 0)
                        self.assertEqual(result["inserted_rows"], 0)
                    else:
                        mocks["delete_recepcion_range"].assert_called_once_with(
                            destination_conn=mocks["open_connection"].return_value,
                            destination_table=config.destination_table,
                            destination_date_column=config.destination_date_column,
                            start_date=self.start_date, end_date=self.end_date,
                            hatcheries=[" INC01 ", "INC02"],
                        )
                        self.assertEqual(result["deleted_rows"], 3)
                        self.assertEqual(result["inserted_rows"], 2)

    def test_insert_failure_rolls_back_in_command_and_dashboard(self):
        from incubacion.views import _run_etl_with_progress

        for route in ("command", "dashboard"):
            with self.subTest(route=route), patch.multiple(
                "incubacion.services", open_connection=DEFAULT, extract_rows_recepcion=DEFAULT,
                delete_recepcion_range=DEFAULT, insert_rows_recepcion=DEFAULT,
            ) as mocks:
                source = Mock()
                destination = Mock()
                mocks["open_connection"].side_effect = [source, destination]
                mocks["extract_rows_recepcion"].return_value = (["No_incubadora"], [("INC01",)])
                mocks["insert_rows_recepcion"].side_effect = RuntimeError("Insert failed")

                with self.assertRaisesRegex(RuntimeError, "Insert failed"):
                    if route == "command":
                        run_etl_recepcion(Mock(), self.start_date, self.end_date, False, 1000)
                    else:
                        _run_etl_with_progress(
                            "recepcion", Mock(), None, self.start_date, self.end_date,
                            False, 1000, Mock(),
                        )

                destination.rollback.assert_called_once_with()
                destination.commit.assert_not_called()
                source.close.assert_called_once_with()
                destination.close.assert_called_once_with()


class IncubesaTests(TestCase):
    def setUp(self):
        self.headers = ["Fecha", "centro_costo", "granja_lote", "Huevo Incubable", "Energia"]
        self.mapping = {"energia": {
            "elemento_costo": "Energia", "grupo_costo": "HAT INC01",
            "objeto_costo": "OBJ01", "SourceCode": "SOURCE", "SystemStageNo": "STAGE",
        }}
        self.start_date = date(2026, 11, 1)
        self.end_date = date(2026, 11, 30)
        self.timestamp = datetime(2026, 11, 9)

    def test_rows_and_keys_use_cleaned_codes(self):
        for center, lot, expected_center, expected_lot in (
            (" INC01 ", "\tLOTE  UNO\u00a0", "INC01", "LOTE  UNO"),
            (" 00123 ", " 00456 ", "00123", "00456"),
            (123, 456, 123, 456),
        ):
            with self.subTest(center=center, lot=lot):
                _, rows, keys, _ = transform_protein_journal_rows(
                    self.mapping, self.headers, [(self.end_date, center, lot, 100, Decimal("12.50"))],
                    self.start_date, self.end_date, self.timestamp,
                )

                self.assertEqual(rows[0][2:4], (expected_center, expected_lot))
                self.assertEqual(rows[0][6], Decimal("12.50"))
                self.assertEqual(rows[0][7], 100)
                self.assertEqual(rows[0][11], self.timestamp)
                self.assertEqual(keys, [(self.end_date, expected_center, expected_lot)])

    def test_blank_and_null_lots_are_normalized_and_sorted_with_text(self):
        _, rows, keys, _ = transform_protein_journal_rows(
            self.mapping, self.headers,
            [(self.end_date, "INC01", lot, 100, 12) for lot in ("LOTE01", None, "", "   ", "\t\u00a0")],
            self.start_date, self.end_date, self.timestamp,
        )

        self.assertEqual([row[3] for row in rows], ["LOTE01", None, None, None, None])
        self.assertEqual(keys, [(self.end_date, "INC01", None), (self.end_date, "INC01", "LOTE01")])

    def test_blank_center_fails_before_destination_is_opened(self):
        for center in (None, "", "   ", "\t\u00a0"):
            with self.subTest(center=center), patch(
                "incubacion.services.read_protein_journal_excel",
                return_value=(self.mapping, self.headers, [
                    (self.end_date, "INC01", "LOTE01", 100, 12),
                    (self.end_date, center, "LOTE02", 100, 12),
                ]),
            ), patch("incubacion.services.open_connection") as opened:
                with self.assertRaisesRegex(ValueError, "Missing centro_costo"):
                    run_etl_protein_journal(
                        Mock(), "mock.xlsx", self.start_date, self.end_date, False, 1000
                    )
                opened.assert_not_called()

    def test_cleaned_keys_delete_only_matching_center_and_lots(self):
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.execute("CREATE TABLE Journal (xDate DATE, centro_costo TEXT, granja_lote TEXT)")
        connection.executemany("INSERT INTO Journal VALUES (?, ?, ?)", [
            ("2026-11-30", "INC01", "LOTE01"), ("2026-11-30", "INC01", None),
            ("2026-11-30", "INC01", "LOTE02"), ("2026-11-30", "INC02", "LOTE01"),
            ("2026-10-31", "INC01", "LOTE01"),
        ])
        _, _, keys, _ = transform_protein_journal_rows(
            self.mapping, self.headers,
            [(self.end_date, " INC01 ", lot, 100, 12) for lot in (" LOTE01 ", None)],
            self.start_date, self.end_date, self.timestamp,
        )

        with patch.dict(sqlite3.adapters, {(date, sqlite3.PrepareProtocol): date.isoformat}):
            deleted = delete_destination_by_keys(
                connection, "Journal", "xDate", "centro_costo", keys, "granja_lote"
            )

        self.assertEqual(deleted, 2)
        self.assertEqual(connection.execute("SELECT * FROM Journal ORDER BY xDate, centro_costo").fetchall(), [
            ("2026-10-31", "INC01", "LOTE01"), ("2026-11-30", "INC01", "LOTE02"),
            ("2026-11-30", "INC02", "LOTE01"),
        ])

    def test_empty_import_and_dry_run_execute_no_database_writes(self):
        for data_rows, dry_run in (([], False), ([(self.end_date, "INC01", "LOTE01", 100, 12)], True)):
            with self.subTest(dry_run=dry_run), patch(
                "incubacion.services.read_protein_journal_excel",
                return_value=(self.mapping, self.headers, data_rows),
            ), patch("incubacion.services.open_connection") as opened:
                result = run_etl_protein_journal(
                    Mock(), "mock.xlsx", self.start_date, self.end_date, dry_run, 1000
                )

                self.assertEqual(result["deleted_rows"], 0)
                self.assertEqual(result["inserted_rows"], 0)
                opened.return_value.cursor.assert_not_called()
                if dry_run:
                    opened.assert_not_called()


class PresupuestoCostCenterTests(TestCase):
    def test_rows_and_keys_use_trimmed_cost_center(self):
        headers = ["Fecha", "centro_costo", "Huevo Incubable", "Pollito aprovechable", "Energia"]
        end_date = date(2026, 11, 30)
        for original, expected in (
            (" INC01 ", "INC01"), ("\tINC  01\u00a0", "INC  01"),
            ("00123 ", "00123"), (123, 123),
        ):
            with self.subTest(original=original):
                _, rows, keys, _ = transform_presupuesto_rows(
                    {"energia": 10}, headers, [(end_date, original, 100, 80, 12)],
                    date(2026, 11, 1), end_date, datetime(2026, 11, 9),
                )

                self.assertEqual(rows[0][1], expected)
                self.assertEqual(keys, [(end_date, expected)])

    def test_blank_cost_centers_generate_no_rows_or_delete_keys(self):
        headers = ["Fecha", "centro_costo", "Huevo Incubable", "Pollito aprovechable", "Energia"]
        end_date = date(2026, 11, 30)
        for blank in (None, "", "   ", "\t\u00a0"):
            with self.subTest(blank=blank):
                _, rows, keys, _ = transform_presupuesto_rows(
                    {"energia": 10}, headers, [(end_date, blank, 100, 80, 12)],
                    date(2026, 11, 1), end_date, datetime(2026, 11, 9),
                )

                self.assertEqual(rows, [])
                self.assertEqual(keys, [])


class IncubacionDashboardTests(TestCase):
    def test_dashboard_scopes_deletion_and_skips_empty_or_dry_run(self):
        from incubacion.views import _run_etl_with_progress

        for rows, dry_run in (([("HAT INC01",)], False), ([], False), ([("HAT INC01",)], True)):
            with self.subTest(rows=rows, dry_run=dry_run), patch.multiple(
                "incubacion.services", open_connection=DEFAULT, extract_rows=DEFAULT,
                delete_incubacion_range=DEFAULT, delete_destination_range=DEFAULT,
                insert_rows=DEFAULT, calculate_data_summary=DEFAULT,
            ) as mocks:
                config = Mock()
                mocks["extract_rows"].return_value = (["grupo_ubicacion"], rows)
                mocks["delete_incubacion_range"].return_value = 2
                mocks["insert_rows"].return_value = len(rows)
                mocks["calculate_data_summary"].return_value = {}

                result = _run_etl_with_progress(
                    "incubacion", config, None, date(2026, 11, 1), date(2026, 11, 9),
                    dry_run, 1000, Mock(),
                )

                mocks["delete_destination_range"].assert_not_called()
                if dry_run or not rows:
                    mocks["delete_incubacion_range"].assert_not_called()
                    mocks["insert_rows"].assert_not_called()
                    self.assertEqual(result["deleted_rows"], 0)
                else:
                    mocks["delete_incubacion_range"].assert_called_once_with(
                        destination_conn=mocks["open_connection"].return_value,
                        destination_table=config.destination_table,
                        destination_date_column=config.destination_date_column,
                        start_date=date(2026, 11, 1), end_date=date(2026, 11, 9),
                        location_groups=["HAT INC01"],
                    )
                    self.assertEqual(result["inserted_rows"], 1)