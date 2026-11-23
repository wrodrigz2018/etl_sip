/* =====================================================================
   LIMPIEZA: quitar espacios en códigos de granja/lote (2026-11-18)
   Causa: la misma granja quedó guardada como 'AH' y 'AH      ',
   y Power BI/Excel las muestran como dos granjas distintas.

   - Hace RESPALDO de cada tabla antes de tocarla (tabla *_bk_20261118).
   - Todo dentro de una transacción: si algo falla, no cambia nada.
   - NO toca dbo.Alojamiento: esa tabla se limpia con
     limpieza_alojamiento.sql, DESPUÉS de instalar la versión del ETL
     que ya carga Alojamiento sin espacios (commit e41d670).
   ===================================================================== */

/* ============================ PARTE 1: BrdZoo ============================ */
USE BrdZoo;
GO
SET XACT_ABORT ON;
BEGIN TRAN;

    SELECT * INTO dbo.ProdHuevos_bk_20261118 FROM dbo.ProdHuevos;

    UPDATE dbo.ProdHuevos
       SET No_granja   = LTRIM(RTRIM(No_granja)),
           Granja_lote = LTRIM(RTRIM(Granja_lote))
     WHERE DATALENGTH(No_granja)   <> DATALENGTH(LTRIM(RTRIM(No_granja)))
        OR DATALENGTH(Granja_lote) <> DATALENGTH(LTRIM(RTRIM(Granja_lote)));

    SELECT @@ROWCOUNT AS prodhuevos_filas_corregidas;   -- esperado ≈ 364 636

COMMIT;
GO

/* ============================ PARTE 2: HtcZoo ============================ */
USE HtcZoo;
GO
SET XACT_ABORT ON;
BEGIN TRAN;

    SELECT * INTO dbo.Ovoscopia_bk_20261118    FROM dbo.Ovoscopia;
    SELECT * INTO dbo.VentaPollito_bk_20261118 FROM dbo.VentaPollito;

    UPDATE dbo.Ovoscopia
       SET No_granja = LTRIM(RTRIM(No_granja)),
           No_lote   = LTRIM(RTRIM(No_lote))
     WHERE DATALENGTH(No_granja) <> DATALENGTH(LTRIM(RTRIM(No_granja)))
        OR DATALENGTH(No_lote)   <> DATALENGTH(LTRIM(RTRIM(No_lote)));

    SELECT @@ROWCOUNT AS ovoscopia_filas_corregidas;    -- esperado ≈ 9 600 o menos

    UPDATE dbo.VentaPollito
       SET granja_lote = LTRIM(RTRIM(granja_lote))
     WHERE DATALENGTH(granja_lote) <> DATALENGTH(LTRIM(RTRIM(granja_lote)));

    SELECT @@ROWCOUNT AS ventapollito_filas_corregidas; -- esperado ≈ 172

COMMIT;
GO

/* Después: volver a correr diagnostico_granjas_repetidas.sql.
   ProdHuevos, Ovoscopia y VentaPollito deben salir con filas_con_espacios = 0
   y sin listas de variantes. Luego actualizar el Power BI/reporte.

   Cuando todo esté verificado (unos días), se pueden borrar los respaldos:
   DROP TABLE BrdZoo.dbo.ProdHuevos_bk_20261118;
   DROP TABLE HtcZoo.dbo.Ovoscopia_bk_20261118;
   DROP TABLE HtcZoo.dbo.VentaPollito_bk_20261118;  */
