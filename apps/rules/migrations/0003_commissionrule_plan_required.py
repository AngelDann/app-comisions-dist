# Generated manually: todas las reglas deben pertenecer a un plan.

import django.db.models.deletion
from django.db import migrations, models


def delete_rules_without_plan(apps, schema_editor):
    HistoricalCommissionRule = apps.get_model("rules", "HistoricalCommissionRule")
    HistoricalCommissionRule.objects.filter(plan_id__isnull=True).delete()
    CommissionRule = apps.get_model("rules", "CommissionRule")
    CommissionRule.objects.filter(plan_id__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rules", "0002_commission_plans"),
    ]

    operations = [
        migrations.RunPython(delete_rules_without_plan, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="commissionrule",
            name="plan",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rules",
                to="rules.commissionplan",
            ),
        ),
    ]
