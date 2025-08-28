from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('modbusapp', '0004_modbusdevice_hr_decimals'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModbusCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('source', models.CharField(choices=[('hr', 'Holding Register'), ('ir', 'Input Register'), ('di', 'Discrete Input'), ('coil', 'Coil')], default='hr', max_length=4)),
                ('address', models.IntegerField(help_text='Absolute Modbus address within the selected source')),
                ('unit_label', models.CharField(blank=True, default='', max_length=32)),
                ('decimals', models.IntegerField(blank=True, help_text='Override decimals for display (optional)', null=True)),
                ('order', models.IntegerField(default=0)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cards', to='modbusapp.modbusdevice')),
            ],
            options={
                'ordering': ['device_id', 'order', 'id'],
            },
        ),
    ]
