from rest_framework import serializers

from depot.models import *


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'


class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = '__all__'

    def create(self, validated_data):
        user = Persona(
            email=validated_data['email'],
            empresa=validated_data['empresa'],
            username=validated_data['username'],
            tipoUsuario=validated_data['tipoUsuario'],
            identificacion=validated_data['identificacion'],
            direccion=validated_data['direccion'],
            is_staff=validated_data['is_staff'],
            telefono=validated_data['telefono'],
            activo=validated_data['activo'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMedida
        fields = '__all__'


class ListProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = [
            'id',
            'empresa',
            'unidadMedida',
            'nombre',
            'precioCompra',
            'precioVenta',
            'codigo',
            'stock',
            'created_at',
            'updated_at',
        ]


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'


class ProductoByNameSerializer(serializers.ModelSerializer):
    nombreUnidad = serializers.ReadOnlyField(source='unidadMedida.abreviatura')
    class Meta:
        model = Producto
        fields = [
                'id',
                'empresa',
                'unidadMedida',
                'nombreUnidad',
                'nombre',
                'nombre_auxiliar',
                'precioCompra',
                'precioVenta',
                'stock',
                'codigo',
                'created_at',
                'updated_at',
            ]

class DocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documento
        fields = '__all__'


class MovesByProductSerializer(serializers.ModelSerializer):
    numero_documento = serializers.ReadOnlyField(source='documento.numeroDocumento')
    tipoDocumento = serializers.ReadOnlyField(source='documento.tipoDocumento')
    nombre_producto = serializers.ReadOnlyField(source='producto.nombre')

    class Meta:
        model = DetalleDocumento
        fields = [
            'id',
            'numero_documento',
            'tipoDocumento',
            'nombre_producto',
            'unidad',
            'vrUnitario',
            'cantidad',
            'total',
            'stockAntes',
            'stockDespues',
            'created_at',
        ]


class DocumentoListSerializer(serializers.ModelSerializer):
    nombre_proveedor = serializers.ReadOnlyField(source='proveedor.nombre')

    class Meta:
        model = Documento
        fields = [
            'id',
            'empresa',
            'proveedor',
            'tipoDocumento',
            'tipoProceso',
            'numeroDocumento',
            'nombre_proveedor',
            'created_at',
        ]


class DetalleDocumentoSerializer(serializers.ModelSerializer):
    producto = serializers.ReadOnlyField(source='producto.nombre')
    producto_id = serializers.ReadOnlyField(source='producto.id')
    codigo = serializers.ReadOnlyField(source='producto.codigo')
    stock = serializers.ReadOnlyField(source='producto.stock')

    class Meta:
        model = DetalleDocumento
        fields = [
            'producto',
            'producto_id',
            'codigo',
            'unidad',
            'vrUnitario',
            'cantidad',
            'total',
            'stock',
            'stockAntes',
            'stockDespues',
            'created_at',
            'updated_at',
        ]


class RecentTransactionsSerializer(serializers.ModelSerializer):
    nombreProducto = serializers.ReadOnlyField(source='producto.nombre')

    class Meta:
        model = DetalleDocumento
        fields = [
            'producto',
            'tipo_movimiento',
            'vrUnitario',
            'cantidad',
            'total',
            'ultimoConteo',
            'nombreProducto',
            'created_at',
            'updated_at',
        ]


class PrecioCompraVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrecioCompraVenta
        fields = '__all__'
