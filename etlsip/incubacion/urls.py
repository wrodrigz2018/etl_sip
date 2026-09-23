from django.urls import path

from incubacion import views

app_name = "incubacion"

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.etl_login, name="etl_login"),
    path("logout/", views.etl_logout, name="etl_logout"),
    path("dashboard/incubacion/", views.etl_dashboard_incubacion, name="etl_dashboard_incubacion"),
    path("dashboard/costo-prod-detalle/", views.etl_dashboard_costo_prod_detalle, name="etl_dashboard_costo_prod_detalle"),
    path("dashboard/presupuesto/", views.etl_dashboard_presupuesto, name="etl_dashboard_presupuesto"),
    path("dashboard/protein-journal/", views.etl_dashboard_protein_journal, name="etl_dashboard_protein_journal"),
    path("dashboard/recepcion/", views.etl_dashboard_recepcion, name="etl_dashboard_recepcion"),
    path("dashboard/cargas/", views.etl_dashboard_cargas, name="etl_dashboard_cargas"),
    path("dashboard/venta-pollito/", views.etl_dashboard_venta_pollito, name="etl_dashboard_venta_pollito"),
    path("dashboard/baja-pollito/", views.etl_dashboard_baja_pollito, name="etl_dashboard_baja_pollito"),
    path("dashboard/ovoscopia/", views.etl_dashboard_ovoscopia, name="etl_dashboard_ovoscopia"),
    path("dashboard/", views.etl_dashboard, name="etl_dashboard"),
    path("execute/incubacion/", views.etl_execute_incubacion, name="etl_execute_incubacion"),
    path("execute/costo-prod-detalle/", views.etl_execute_costo_prod_detalle, name="etl_execute_costo_prod_detalle"),
    path("execute/presupuesto/", views.etl_execute_presupuesto, name="etl_execute_presupuesto"),
    path("execute/protein-journal/", views.etl_execute_protein_journal, name="etl_execute_protein_journal"),
    path("execute/recepcion/", views.etl_execute_recepcion, name="etl_execute_recepcion"),
    path("execute/cargas/", views.etl_execute_cargas, name="etl_execute_cargas"),
    path("execute/venta-pollito/", views.etl_execute_venta_pollito, name="etl_execute_venta_pollito"),
    path("execute/baja-pollito/", views.etl_execute_baja_pollito, name="etl_execute_baja_pollito"),
    path("execute/ovoscopia/", views.etl_execute_ovoscopia, name="etl_execute_ovoscopia"),
    path("execute/", views.etl_execute, name="etl_execute"),
    path("preview/incubacion/", views.etl_preview_incubacion, name="etl_preview_incubacion"),
    path("preview/costo-prod-detalle/", views.etl_preview_costo_prod_detalle, name="etl_preview_costo_prod_detalle"),
    path("preview/presupuesto/", views.etl_preview_presupuesto, name="etl_preview_presupuesto"),
    path("preview/protein-journal/", views.etl_preview_protein_journal, name="etl_preview_protein_journal"),
    path("preview/recepcion/", views.etl_preview_recepcion, name="etl_preview_recepcion"),
    path("preview/cargas/", views.etl_preview_cargas, name="etl_preview_cargas"),
    path("preview/venta-pollito/", views.etl_preview_venta_pollito, name="etl_preview_venta_pollito"),
    path("preview/baja-pollito/", views.etl_preview_baja_pollito, name="etl_preview_baja_pollito"),
    path("preview/ovoscopia/", views.etl_preview_ovoscopia, name="etl_preview_ovoscopia"),
    path("preview/", views.etl_preview, name="etl_preview"),
    path("status/", views.etl_status, name="etl_status"),
    path("history/", views.etl_history, name="etl_history"),
]
