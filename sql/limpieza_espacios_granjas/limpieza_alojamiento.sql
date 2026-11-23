/* =====================================================================
   LIMPIEZA dbo.Alojamiento (BrdZoo) - correr DESPUÉS de instalar el zip
   Quita los espacios de Granja_lote y Granja_galpon (587 filas al 18-nov).
   Hace respaldo y va en transacción.
   ===================================================================== */
USE BrdZoo;
GO
SET XACT_ABORT ON;
BEGIN TRAN;

    SELECT * INTO dbo.Alojamiento_bk_20261118 FROM dbo.Alojamiento;

    UPDATE dbo.Alojamiento
       SET No_granja     = LTRIM(RTRIM(No_granja)),
           Granja_lote   = LTRIM(RTRIM(Granja_lote)),
           Lote_galpon   = LTRIM(RTRIM(Lote_galpon)),
           no_galpon     = LTRIM(RTRIM(no_galpon)),
           Granja_galpon = LTRIM(RTRIM(Granja_galpon))
     WHERE DATALENGTH(No_granja)     <> DATALENGTH(LTRIM(RTRIM(No_granja)))
        OR DATALENGTH(Granja_lote)   <> DATALENGTH(LTRIM(RTRIM(Granja_lote)))
        OR DATALENGTH(Lote_galpon)   <> DATALENGTH(LTRIM(RTRIM(Lote_galpon)))
        OR DATALENGTH(no_galpon)     <> DATALENGTH(LTRIM(RTRIM(no_galpon)))
        OR DATALENGTH(Granja_galpon) <> DATALENGTH(LTRIM(RTRIM(Granja_galpon)));

    SELECT @@ROWCOUNT AS alojamiento_filas_corregidas;   -- esperado ≈ 587

COMMIT;
GO

/* Cuando esté verificado: DROP TABLE BrdZoo.dbo.Alojamiento_bk_20261118; */
