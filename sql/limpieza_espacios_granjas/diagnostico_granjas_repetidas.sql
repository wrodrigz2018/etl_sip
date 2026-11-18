/* =====================================================================
   DIAGNÓSTICO: granjas repetidas en tablas cargadas por el ETL SIP
   SOLO LECTURA (únicamente SELECT). Correr en SSMS en cada base destino
   (HtcZoo y BrdZoo); las tablas que no existan en esa base se saltan.

   Qué busca:
   A) Mismo código de granja/lote guardado con espacios distintos
      ('C34' vs 'C34   ' o ' C34'). SQL Server los agrupa igual, pero
      Power BI / Excel / Python los ven como granjas distintas.
   B) Filas duplicadas (misma clave cargada más de una vez).
   ===================================================================== */
SET NOCOUNT ON;

DECLARE @checks TABLE (tabla sysname, columna sysname);
INSERT INTO @checks VALUES
 ('dbo.Recepcion','No_granja'), ('dbo.Recepcion','No_lote'),
 ('dbo.HuevosVendidos','no_granja'), ('dbo.HuevosVendidos','granja_lote'),
 ('dbo.ProdHuevos','No_granja'), ('dbo.ProdHuevos','Granja_lote'),
 ('dbo.Alojamiento','No_granja'), ('dbo.Alojamiento','Granja_lote'),
 ('dbo.Alojamiento','Lote_galpon'), ('dbo.Alojamiento','Granja_galpon'),
 ('dbo.Ovoscopia','No_granja'), ('dbo.Ovoscopia','No_lote'),
 ('dbo.VentaPollito','granja_lote'),
 ('dbo.CostoProdDetalle','granja_lote');

DECLARE @t sysname, @c sysname, @sql nvarchar(max);
DECLARE cur CURSOR LOCAL FAST_FORWARD FOR SELECT tabla, columna FROM @checks;
OPEN cur;
FETCH NEXT FROM cur INTO @t, @c;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF COL_LENGTH(@t, @c) IS NOT NULL
    BEGIN
        /* A1) Resumen: cuántas filas tienen espacios al inicio/final */
        SET @sql = N'
        SELECT ''' + @t + N''' AS tabla, ''' + @c + N''' AS columna,
               COUNT(*) AS filas_total,
               SUM(CASE WHEN DATALENGTH(' + QUOTENAME(@c) + N') <> DATALENGTH(LTRIM(RTRIM(' + QUOTENAME(@c) + N')))
                        THEN 1 ELSE 0 END) AS filas_con_espacios,
               (SELECT TOP 1 DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
                 WHERE TABLE_SCHEMA = PARSENAME(''' + @t + N''',2)
                   AND TABLE_NAME = PARSENAME(''' + @t + N''',1)
                   AND COLUMN_NAME = ''' + @c + N''') AS tipo_dato
        FROM ' + @t + N';';
        EXEC sp_executesql @sql;

        /* A2) Detalle: códigos que aparecen con más de una "variante" */
        SET @sql = N'
        SELECT TOP 50 ''' + @t + N''' AS tabla, ''' + @c + N''' AS columna,
               LTRIM(RTRIM(' + QUOTENAME(@c) + N')) AS codigo_limpio,
               COUNT(DISTINCT ''['' + ' + QUOTENAME(@c) + N' + '']'') AS variantes,
               MIN(''['' + ' + QUOTENAME(@c) + N' + '']'') AS ejemplo_1,
               MAX(''['' + ' + QUOTENAME(@c) + N' + '']'') AS ejemplo_2,
               COUNT(*) AS filas
        FROM ' + @t + N'
        WHERE ' + QUOTENAME(@c) + N' IS NOT NULL
        GROUP BY LTRIM(RTRIM(' + QUOTENAME(@c) + N'))
        HAVING COUNT(DISTINCT ''['' + ' + QUOTENAME(@c) + N' + '']'') > 1
        ORDER BY filas DESC;';
        EXEC sp_executesql @sql;
    END
    FETCH NEXT FROM cur INTO @t, @c;
END
CLOSE cur; DEALLOCATE cur;

/* A3) ¿Desde qué fecha cambió? (ProdHuevos: filas con espacios por mes) */
IF OBJECT_ID('dbo.ProdHuevos') IS NOT NULL
    EXEC('SELECT ''dbo.ProdHuevos'' AS tabla, YEAR(fecha)*100+MONTH(fecha) AS periodo,
                 COUNT(*) AS filas,
                 SUM(CASE WHEN DATALENGTH(Granja_lote) <> DATALENGTH(LTRIM(RTRIM(Granja_lote))) THEN 1 ELSE 0 END) AS con_espacios
          FROM dbo.ProdHuevos GROUP BY YEAR(fecha)*100+MONTH(fecha) ORDER BY periodo DESC;');

/* B) Filas duplicadas */
IF OBJECT_ID('dbo.CostoProdDetalle') IS NOT NULL
    EXEC('SELECT TOP 50 ''dbo.CostoProdDetalle'' AS tabla, LTRIM(RTRIM(granja_lote)) AS granja_lote,
                 no_incubadora, fecha_inicio_mes, COUNT(*) AS repeticiones
          FROM dbo.CostoProdDetalle
          GROUP BY LTRIM(RTRIM(granja_lote)), no_incubadora, fecha_inicio_mes
          HAVING COUNT(*) > 1 ORDER BY repeticiones DESC;');

IF OBJECT_ID('dbo.Ovoscopia') IS NOT NULL AND COL_LENGTH('dbo.Ovoscopia','IRN') IS NOT NULL
    EXEC('SELECT TOP 50 ''dbo.Ovoscopia'' AS tabla, IRN, COUNT(*) AS repeticiones
          FROM dbo.Ovoscopia GROUP BY IRN HAVING COUNT(*) > 1 ORDER BY repeticiones DESC;');

IF OBJECT_ID('dbo.Alojamiento') IS NOT NULL
    EXEC('SELECT TOP 50 ''dbo.Alojamiento'' AS tabla, LTRIM(RTRIM(Lote_galpon)) AS lote_galpon, Fecha,
                 COUNT(*) AS repeticiones
          FROM dbo.Alojamiento
          GROUP BY LTRIM(RTRIM(Lote_galpon)), Fecha
          HAVING COUNT(*) > 2   -- normal: hasta 2 (hembras/machos)
          ORDER BY repeticiones DESC;');
