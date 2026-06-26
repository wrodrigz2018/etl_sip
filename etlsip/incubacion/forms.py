from datetime import date

from django import forms


class ETLExecutionForm(forms.Form):
    start_date = forms.DateField(
        label="Fecha de Inicio",
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control",
            "required": "required",
        }),
        help_text="Fecha inicial del rango a procesar (YYYY-MM-DD)",
    )
    end_date = forms.DateField(
        label="Fecha de Fin",
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control",
            "required": "required",
        }),
        help_text="Fecha final del rango a procesar (YYYY-MM-DD)",
    )
    batch_size = forms.IntegerField(
        label="Tamaño de Lote",
        initial=1000,
        min_value=1,
        max_value=10000,
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "type": "number",
            "min": "1",
            "max": "10000",
        }),
        help_text="Número de registros por batch (1-10000, defecto: 1000)",
    )
    dry_run = forms.BooleanField(
        label="Modo de Prueba (Dry Run)",
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
        }),
        help_text="Si está marcado, extrae datos sin borrar ni insertar en destino",
    )

    def clean(self) -> dict:
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError(
                    "La fecha de fin debe ser mayor o igual a la fecha de inicio."
                )

        return cleaned_data
