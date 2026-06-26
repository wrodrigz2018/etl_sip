SELECT
    -- Dimensiones principales
    be.GenerationCode            AS codigo_generacion,
    r.CostCenterNo               AS centro_costo,
    r.HatcheryNo                 AS no_incubadora,
    be.ComplexEntityNo           AS granja_lote,   
    
    (SELECT DivisionNo FROM mtech.ProteinDivisions 
    WHERE IRN = pc.ProteinDivisionsIRN) 
    AS No_Division,

    -- Fechas
    MAX(r.BegDate) AS fecha_inicio_mes,
    MAX(r.EndDate) AS fecha_fin_mes,

    -- ===== HUEVOS (ER = Egg Room / Egg Recon) =====
    SUM(r.ERStageAllocationAmount)   AS ER_StageAlloc,
    SUM(r.EROpsAllocationAmount)     AS ER_OpsAlloc,
    SUM(r.EREggsPurchasedValue)      AS ER_Compra_Valor,
    SUM(r.EREggsPurchasedUnits)      AS ER_Compra_Unidades,
    SUM(r.EREggsReceivedValue)       AS ER_Recepcion_Valor,
    SUM(r.EREggsReceivedUnits)       AS ER_Recepcion_Unidades,
    SUM(r.EREggsDisposedUnits)       AS ER_Eliminados,
    SUM(r.EREggsDowngradeUnits)      AS ER_BajasCalidad,
    SUM(r.EREggsTransferredInUnits)  AS ER_Transfer_Entrada,
    SUM(r.EREggsTransferredOutUnits) AS ER_Transfer_Salida,
    SUM(r.EREggsSoldUnits)           AS ER_Ventas_Unidades,

    SUM(r.ERbeginningInventoryUnits) AS ER_InvInicial_Unidades,
    SUM(r.ERbeginningInventoryValue) AS ER_InvInicial_Valor,
    SUM(r.ERendingInventoryUnits)    AS ER_InvFinal_Unidades,
    SUM(r.ERendingInventoryValue)    AS ER_InvFinal_Valor,

        -- ===== HUEVOS (SR = Set Room / Egg Recon) =====    
    SUM([SRBeginningInventoryUnits]) AS SR_InvInicial_Unidades,
    SUM([SRBeginningInventoryValue]) AS SR_InvInicial_Valor,
    SUM([SREggsSetUnits]) AS SR_HICargado_Unidades,
    SUM([SREggsSetValue]) AS SR_HICargado_Valor,
    SUM([SREggsTransferredUnits]) AS SR_Transferencia_unidades,
    SUM([SREggsTransferredValue]) AS SR_Transferencia_valor,
    SUM([SREndingInventoryUnits]) AS SR_InvFinal_Unidades,
    SUM([SREndingInventoryValue]) AS SR_InvFinal_Valor,
    SUM([SROpsAllocationAmount]) AS SR_DistrCIF_Valor,
    SUM([SRStageAllocationAmount]) AS SR_DistrCostos_Etapa,
    SUM([SREggsDisposedUnits]) as SR_HuevoDesecho_Unidades,
    SUM([SRBeginningInventoryUnits])+SUM([SREggsSetUnits])-SUM([SREggsTransferredUnits])-SUM([SREndingInventoryUnits]) AS SR_HuevoDesecho_Unidades,

        -- ===== HUEVOS (HR = Hatch Room / Egg Recon) =====  

    SUM([HRBeginningInventoryUnits]) AS HR_InvInicial_Unidades,
    SUM([HRBeginningInventoryValue]) AS HR_InvInicial_Valor,
    SUM([HREggsTransferredInUnits]) AS HR_TransfIngreso_Unidades,
    SUM([HREggsTransferredInValue]) AS HR_TransfIngreso_Valor,
    SUM([HREggsHatchedUnits]) as HR_PollosNacidos_Unidades,
    SUM([HREggsHatchedValue]) as HR_PollosNacidos_Valor,
    SUM([HREndingInventoryUnits]) as HR_InvFinal_Unidades,
    SUM([HREggsHatchedValue]) as HR_InvFinal_Valor,    
    SUM([HRStageAllocationAmount]) as HR_CostosEtapa_Valor,
    SUM([HROpsAllocationAmount]) as HR_DistCIF_Valor,

    -- ===== POLLOS (CHICKS) =====
    r.ChickBeginningInventoryUnits   AS Pollitos_InvInicial,
    r.ChickBeginningInventoryValue   AS Pollitos_InvInicial_Valor,
    SUM(r.ChicksHatchedUnits)        AS Pollitos_Nacidos,
    SUM(r.ChicksHatchedAmount)       AS Pollitos_Nacidos_Valor,
    SUM(r.ChicksTransferredInUnits)  AS Pollitos_TransferEntrada,
    SUM(r.ChicksTransferredInValue)  AS Pollitos_TransferEntrada_Valor,
    SUM(r.ChicksTransferredOutUnits) AS Pollitos_TransferSalida,
    SUM(r.ChicksTransferredOutValue) AS Pollitos_TransferSalida_Valor,
    SUM(r.ChicksPurchasedUnits)      AS Pollitos_Comprados,
    SUM(r.ChicksDisposedUnits)       AS Pollitos_Eliminados,
    SUM([ChicksOpsAllocationAmount]) AS Pollitos_DistrCIF_Valor,
    SUM(r.ChicksPlacedUnits)         AS Pollitos_Alojados,
    SUM(r.ChicksPlacedValue)         AS Pollitos_Alojados_Valor,
    SUM(r.ChicksSoldUnits)           AS Pollitos_Vendidos,
    SUM(r.ChicksSoldValue)           AS Pollitos_Vendidos_Valor,
    -- Inventarios de pollitos (no agregados intencionalmente)    
    r.ChickEndingInventoryUnits      AS Pollitos_InvFinal_Unidades,
    r.ChickEndingInventoryValue      AS Pollitos_InvFinal_Valor

FROM mtech.mvHimPELogEggFlowRecon r

LEFT JOIN mtech.ProteinCostCenters pc 
    ON pc.IRN = r.ProteinCostCentersIRN

LEFT JOIN mtech.ProteinEntities pe 
    ON pe.IRN = r.ProteinEntitiesIRN

LEFT JOIN mtech.mvBimEntities be 
    ON pe.IRN = be.ProteinEntitiesIRN

WHERE 
    r.EndDate BETWEEN '2026-05-31' AND '2026-05-31'
    AND r.BegDate BETWEEN '2026-05-01' AND '2026-05-01'
    AND r.HatcheryNo IN ('AVEGUAYAS', 'AVEPICA', 'INCA')
    AND r.SpeciesType = 1
    AND r.FarmType = 2

GROUP BY 
    be.GenerationCode,
    be.ComplexEntityNo,
    r.CostCenterNo,
    r.HatcheryNo,
    pc.ProteinDivisionsIRN,
    r.ChickBeginningInventoryUnits,
    r.ChickBeginningInventoryValue,
    r.ChickEndingInventoryUnits,
    r.ChickEndingInventoryValue

ORDER BY 
    r.CostCenterNo,
    r.HatcheryNo;
