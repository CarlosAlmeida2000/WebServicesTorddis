# Generated by Django 3.0.8 on 2022-11-28 14:13

from django.db import migrations, models
import django.db.models.deletion
import fernet_fields.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Personas',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombres', models.CharField(max_length=40)),
                ('apellidos', models.CharField(max_length=40)),
                ('fecha_nacimiento', models.DateField()),
                ('foto_perfil', models.ImageField(blank=True, null=True, upload_to='Perfiles')),
            ],
        ),
        migrations.CreateModel(
            name='Tutores',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('usuario', models.CharField(max_length=20, unique=True)),
                ('clave', fernet_fields.fields.EncryptedTextField()),
                ('correo', models.CharField(max_length=100)),
                ('persona', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='Persona.Personas')),
            ],
        ),
        migrations.CreateModel(
            name='Supervisados',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('persona', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='Persona.Personas')),
                ('tutor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='Persona.Tutores')),
            ],
        ),
    ]
