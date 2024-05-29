from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class Empresa(models.Model):
    nit = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=100)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    correo = models.EmailField(unique=True)


class Persona(AbstractUser):
    TIPOS_USUARIO = [
        ('Cliente', 'Cliente'),
        ('Empleado', 'Empleado'),
        ('Administrador', 'Administrador'),
        ('Proveedor', 'Proveedor'),
    ]
    empresa = models.ForeignKey('Empresa', null=True, on_delete=models.PROTECT)
    nombre = models.CharField(max_length=100)
    identificacion = models.CharField(max_length=100, blank=True, null=True, unique=True)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    tipoUsuario = models.CharField(max_length=13, choices=TIPOS_USUARIO)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)


class Proveedor(models.Model):
    empresa = models.ForeignKey('Empresa', null=True, on_delete=models.PROTECT)
    nit = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=100)
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    correo = models.EmailField(unique=True,blank=True, null=True)


class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=50)
    abreviatura = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.abreviatura = self.abreviatura.lower()  # convert to uppercase
        super().save(*args, **kwargs)


class Producto(models.Model):
    empresa = models.ForeignKey('Empresa', on_delete=models.PROTECT)
    unidadMedida = models.ForeignKey('UnidadMedida', on_delete=models.PROTECT, null=True, blank=True)
    nombre = models.CharField(max_length=100, unique=True)
    nombre_auxiliar = models.CharField(max_length=100, default='', null=True, blank=True)
    precioCompra = models.PositiveIntegerField()
    precioVenta = models.PositiveIntegerField()
    stock = models.PositiveBigIntegerField()
    codigo = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # elimina los espacios en blanco del campo nombre
        self.nombre_auxiliar = slugify(self.nombre.lower())
        super(Producto, self).save(*args, **kwargs)


class Documento(models.Model):
    TIPOS_DOCUMENTO = [
        ('Entrada', 'Entrada'),
        ('Salida', 'Salida'),
    ]
    TIPOS_PROCESO = [
        ('Manual', 'Manual'),
        ('Automatico', 'Automatico'),
    ]
    empresa = models.ForeignKey('Empresa', on_delete=models.PROTECT)
    proveedor = models.ForeignKey('Proveedor', null=True, on_delete=models.PROTECT)
    tipoDocumento = models.CharField(max_length=7, choices=TIPOS_DOCUMENTO)
    tipoProceso = models.CharField(max_length=12, choices=TIPOS_PROCESO)
    numeroDocumento = models.CharField(max_length=100, default=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DetalleDocumento(models.Model):
    documento = models.ForeignKey(Documento, on_delete=models.PROTECT, related_name='docCount')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='stockCount')
    unidad = models.CharField(max_length=100, default=True, blank=True, null=True)
    vrUnitario = models.PositiveIntegerField()
    cantidad = models.PositiveBigIntegerField()
    total = models.PositiveBigIntegerField()
    stockAntes = models.PositiveBigIntegerField()
    stockDespues = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PrecioCompraVenta(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
