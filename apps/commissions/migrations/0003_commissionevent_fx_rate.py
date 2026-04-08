import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("commissions", "0002_initial"),
        ("fx", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="commissionevent",
            name="fx_rate",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="commission_events",
                to="fx.fxrate",
                help_text="Si se indica, el monto del evento está en fx_rate.currency_code y se convierte con fx_rate.value (unidades de moneda base por 1 unidad de esa moneda).",
            ),
        ),
    ]
