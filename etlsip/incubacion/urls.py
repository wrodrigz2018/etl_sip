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
    path("dashboard/", views.etl_dashboard, name="etl_dashboard"),
    path("execute/incubacion/", views.etl_execute_incubacion, name="etl_execute_incubacion"),
    path("execute/costo-prod-detalle/", views.etl_execute_costo_prod_detalle, name="etl_execute_costo_prod_detalle"),
    path("execute/presupuesto/", views.etl_execute_presupuesto, name="etl_execute_presupuesto"),
    path("execute/", views.etl_execute, name="etl_execute"),
    path("preview/incubacion/", views.etl_preview_incubacion, name="etl_preview_incubacion"),
    path("preview/costo-prod-detalle/", views.etl_preview_costo_prod_detalle, name="etl_preview_costo_prod_detalle"),
    path("preview/presupuesto/", views.etl_preview_presupuesto, name="etl_preview_presupuesto"),
    path("preview/", views.etl_preview, name="etl_preview"),
    path("status/", views.etl_status, name="etl_status"),
    path("history/", views.etl_history, name="etl_history"),
]
