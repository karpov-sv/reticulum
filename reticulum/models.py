# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Sequences(models.Model):
    path = models.TextField(unique=True, blank=True, null=True)
    site = models.TextField(blank=True, null=True)
    observer = models.TextField(blank=True, null=True)
    filter = models.TextField(blank=True, null=True)
    target = models.TextField(blank=True, null=True)
    moc = models.TextField(blank=True, null=True)
    keywords = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sequences'


class Frames(models.Model):
    sequence = models.ForeignKey(Sequences, on_delete=models.DO_NOTHING, db_column='sequence', blank=True, null=True)
    time = models.DateTimeField(blank=True, null=True)
    filter = models.TextField(blank=True, null=True)
    exposure = models.FloatField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    radius = models.FloatField(blank=True, null=True)
    pixscale = models.FloatField(blank=True, null=True)
    width = models.IntegerField(blank=True, null=True)
    height = models.IntegerField(blank=True, null=True)
    moc = models.TextField(blank=True, null=True)
    keywords = models.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'frames'
        unique_together = (('sequence', 'time'),)


class Photometry(models.Model):
    sequence = models.ForeignKey(Sequences, on_delete=models.DO_NOTHING, db_column='sequence', blank=True, null=True)
    frame = models.ForeignKey(Frames, on_delete=models.DO_NOTHING, db_column='frame', blank=True, null=True)
    time = models.DateTimeField(blank=True, null=True)
    filter = models.TextField(blank=True, null=True)
    ra = models.FloatField(blank=True, null=True)
    dec = models.FloatField(blank=True, null=True)
    mag = models.FloatField(blank=True, null=True)
    magerr = models.FloatField(blank=True, null=True)
    color_term = models.FloatField(blank=True, null=True)
    color_term2 = models.FloatField(blank=True, null=True)
    flags = models.IntegerField(blank=True, null=True)
    fwhm = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'photometry'
