import json
import re
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError, GoogleAuthError
from openai import OpenAI
from rest_framework import viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
import google.generativeai as geneai
from google.oauth2 import service_account
from google.cloud import speech
from .serializers import *
from django.db.models import Q
from functools import reduce
import operator


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer


class PersonaViewSet(viewsets.ModelViewSet):
    queryset = Persona.objects.all()
    serializer_class = PersonaSerializer


class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer


class UnidadMedidaViewSet(viewsets.ModelViewSet):
    queryset = UnidadMedida.objects.all()
    serializer_class = UnidadMedidaSerializer


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer


class ListProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ListProductoSerializer


class DetalleMovimeintoViewSet(viewsets.ModelViewSet):
    queryset = DetalleDocumento.objects.all()
    serializer_class = DetalleDocumentoSerializer


class DocumentosViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentoListSerializer
    queryset = Documento.objects.all().order_by('-id')


class DocumentosByEmpresaViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentoSerializer

    def get_queryset(self):
        empresa_id = self.request.query_params.get('empresa_id')
        queryset = Documento.objects.filter(empresa_id=empresa_id).order_by('-id')[:20]
        return queryset


class MovesByProductViewSet(viewsets.ModelViewSet):
    serializer_class = MovesByProductSerializer

    def get_queryset(self):
        producto_id = self.request.query_params.get('producto_id')
        empresa_id = self.request.query_params.get('empresa_id')
        queryset = DetalleDocumento.objects.filter(
            documento__empresa_id=empresa_id,
            producto_id=producto_id,
        ).order_by('-id')[:20]
        return queryset


class DetalleDocuemntoByDocumentoViewSet(viewsets.ModelViewSet):
    serializer_class = DetalleDocumentoSerializer

    def get_queryset(self):
        documento_id = self.request.query_params.get('documento_id')
        queryset = DetalleDocumento.objects.filter(documento_id=documento_id).order_by('-id')[:10]
        return queryset


class ProductByNameViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoByNameSerializer

    def get_queryset(self):
        empresa = self.request.query_params.get('empresa')
        prod_name = self.request.query_params.get('prod_name')
        queryset = Producto.objects.filter(empresa_id=empresa, nombre__icontains=prod_name).order_by('nombre')
        return queryset


class ObtainToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        user.token = token.key
        usuario = PersonaSerializer(user)
        return Response(usuario.data)


class ExtractJsonView(APIView):

    def post(self, request, *args, **kwargs):
        try:
            text = request.data['text']
            cleaned_json_string = self.extract_json(text)
            data = self.parse_json(cleaned_json_string)
            if not data.get('productos'):
                return Response({'message': 'Lo siento no pude procesar tu solicitud.', 'success': False},
                                status=status.HTTP_200_OK)

            self.buscar_y_actualizar_stock(data['productos'])

            return Response({'message': '!Lo tengo!, ya esta lista tu peticion...', 'success': True,
                             'data': data['productos']}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f'Error: {str(e)}')
            mensaje = {'message': 'Error en el servidor.'}
            return Response(mensaje, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def extract_json(self, text):
        question = (f'Por favor, utiliza el siguiente texto: {text}. como base para generar un JSON con '
                    f'información de productos. El JSON debe contener un array llamado "productos", donde cada elemento '
                    f'represente un producto con dos campos: "producto" para el nombre del producto y "cantidad" para '
                    f'la cantidad en números.')
        print(question)
        client = OpenAI(api_key='API KEY GPT HERE')
        response_text = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=question,
            max_tokens=500,
            temperature=0,
        )
        cleaned_json_string = response_text.choices[0].text.strip()
        match_start = re.search(r'{', cleaned_json_string)
        match_end = re.search(r'}', cleaned_json_string[::-1])
        if match_start and match_end:
            # Calcula las posiciones de las llaves en la cadena original
            start_pos = match_start.start()
            end_pos = len(cleaned_json_string) - match_end.start()
            # Extrae la subcadena entre las llaves
            json_substring = cleaned_json_string[start_pos:end_pos]
        else:
            json_substring = {}
        return json_substring

    def parse_json(self, json_string):
        try:
            data = json.loads(json_string)
            return data
        except json.JSONDecodeError:
            raise ValueError('Error al decodificar el JSON.')

    def buscar_y_actualizar_stock(self, productos_json):
        resultados = []

        for producto_json in productos_json:
            nombre_producto = producto_json.get("producto")

            palabras = nombre_producto.split()
            # construimos nuestras consultas Q dinámicamente con todas las palabras
            queries = [Q(nombre__icontains=palabra.lower()) for palabra in palabras]
            # combinamos todas nuestras consultas Q usando el operador OR (|)
            query = reduce(operator.or_, queries)
            # Buscar el producto por nombre (ignorando mayúsculas/minúsculas y tildes)
            productos_encontrados = Producto.objects.filter(query)

            if len(productos_encontrados) > 1:
                # Si hay más de una coincidencia, crear un dataset con la información adicional
                dataset = [
                    {
                        "producto": producto.nombre,
                        "producto_id": producto.id,
                        "codigo": producto.codigo,
                        "unidad": producto.unidadMedida.abreviatura,
                        "encontrado": True,
                        "precioVenta": producto.precioVenta,
                        "cantidad_en_stock": producto.stock,
                        "selected": False
                    }
                    for producto in productos_encontrados]
                producto_json["dataset"] = dataset
                producto_json["encontrado"] = False
                producto_json["selected"] = False
            elif len(productos_encontrados) == 1:
                # Si hay exactamente una coincidencia, actualizar el JSON con información adicional
                producto_encontrado = productos_encontrados[0]
                producto_json.update({
                    "encontrado": True,
                    "producto": producto_encontrado.nombre,
                    "producto_id": producto_encontrado.id,
                    "codigo": producto_encontrado.codigo,
                    "unidad": producto_encontrado.unidadMedida.abreviatura,
                    "precioVenta": producto_encontrado.precioVenta,
                    "cantidad_en_stock": producto_encontrado.stock,
                    "dataset": [],
                    "selected": True
                })
            else:
                # Si no se encuentra ningún producto, establecer "encontrado" en False y la cantidad en 0
                producto_json.update({
                    "encontrado": False,
                    "selected": False,
                    "producto": nombre_producto,
                    "dataset": []
                })

            resultados.append(producto_json)
        print(resultados)
        return resultados


class ExtractJsonProveedorView(APIView):

    def post(self, request, *args, **kwargs):
        try:
            text = request.data['text']
            cleaned_json_string = self.extract_json(text)
            data = self.parse_json(cleaned_json_string)
            if not data.get('productos'):
                return Response({'message': 'Lo siento no pude procesar tu solicitud.', 'success': False},
                                status=status.HTTP_200_OK)

            return Response({'message': '!Lo tengo!, ya esta lista tu peticion...', 'success': True,
                             'data': data['productos']}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f'Error: {str(e)}')
            mensaje = {'message': 'Error en el servidor.'}
            return Response(mensaje, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def extract_json(self, text):
        question = (f'Por favor, utiliza el siguiente texto: {text}. como base para generar un JSON con '
                    f'información de productos. El JSON debe contener un array llamado "productos", donde cada elemento '
                    f'represente un producto con dos campos: "producto" para el nombre del producto y "cantidad" para '
                    f'la cantidad en números.')
        print(question)
        client = OpenAI(api_key='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')
        response_text = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=question,
            max_tokens=500,
            temperature=0,
        )
        cleaned_json_string = response_text.choices[0].text.strip()
        match_start = re.search(r'{', cleaned_json_string)
        match_end = re.search(r'}', cleaned_json_string[::-1])
        if match_start and match_end:
            # Calcula las posiciones de las llaves en la cadena original
            start_pos = match_start.start()
            end_pos = len(cleaned_json_string) - match_end.start()
            # Extrae la subcadena entre las llaves
            json_substring = cleaned_json_string[start_pos:end_pos]
        else:
            json_substring = {}
        return json_substring

    def parse_json(self, json_string):
        try:
            data = json.loads(json_string)
            return data
        except json.JSONDecodeError:
            raise ValueError('Error al decodificar el JSON.')


class ExtractJsonProductQueryView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            text = request.data['text']
            cleaned_json_string = self.extract_json(text)
            data = self.parse_json(cleaned_json_string)
            print(data)
            productos = Producto.objects.filter(**data)
            prodsSelialized = ProductoByNameSerializer(productos,many=True)
            return Response({'message': '!Lo tengo!, ya esta lista tu peticion...', 'success': True,
                             'data': prodsSelialized.data}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f'Error: {str(e)}')
            mensaje = {'message': 'Error en el servidor.'}
            return Response(mensaje, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def extract_json(self, text):
        question = (f'teniendo en cuenta que el Modelo Producto tiene los siguientes campos:unidadMedida(relcion),'
                    f'nombre,'
                    f'precioCompra,precioVenta, stock,codigo,created_at,updated_at y el modelo UnidadMedida tien '
                    f'los siguientes campos: nombre. crear los KeyWord arguments de '
                    f'la consulta  a partir del siguiente texto:{text}. en formato JSON')

        print(question)
        client = OpenAI(api_key='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')
        response_text = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=question,
            max_tokens=500,
            temperature=0,
        )
        cleaned_json_string = response_text.choices[0].text.strip()
        match_start = re.search(r'{', cleaned_json_string)
        match_end = re.search(r'}', cleaned_json_string[::-1])
        if match_start and match_end:
            # Calcula las posiciones de las llaves en la cadena original
            start_pos = match_start.start()
            end_pos = len(cleaned_json_string) - match_end.start()
            # Extrae la subcadena entre las llaves
            json_substring = cleaned_json_string[start_pos:end_pos]
        else:
            json_substring = {}
        print(json_substring)
        return json_substring

    def parse_json(self, json_string):
        try:
            data = json.loads(json_string)
            return data
        except json.JSONDecodeError:
            raise ValueError('Error al decodificar el JSON.')


class GuardarDocumentoView(APIView):
    def post(self, request, *args, **kwargs):
        try:

            dataSet = request.data['detalleDocumento']
            empresa = int(request.data['empresa'])
            proveedor = int(request.data['proveedor'])
            tipoDocumento = request.data['tipoDocumento']
            tipoProceso = request.data['tipoProceso']
            numeroDocumento = request.data['numeroDocumento']

            empresaTemp = Empresa.objects.get(id=empresa)
            proveedorTemp = Proveedor.objects.get(id=proveedor)
            documento = Documento.objects.create(
                empresa=empresaTemp,
                proveedor=proveedorTemp,
                tipoDocumento=tipoDocumento,
                tipoProceso=tipoProceso,
                numeroDocumento=numeroDocumento,
            )

            for data in dataSet:
                dataJson = json.loads(data)
                if dataJson['encontrado']:
                    if tipoDocumento == 'Entrada':
                        self.crear_movimiento_suma(dataJson, documento)
                    else:
                        self.crear_movimiento_resta(dataJson, documento)

            mensaje = {'message': 'Movimiento creado exitosamente.', 'success': True}
            return Response(mensaje, status=status.HTTP_200_OK)

        except Exception as e:
            print(f'Error: {str(e)}')
            mensaje = {'message': 'Error en el servidor.'}
            return Response(mensaje, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def crear_movimiento_suma(self, detalle, documento):
        try:

            producto_encontrado = Producto.objects.get(id=int(detalle['producto_id']))
            DetalleDocumento.objects.create(
                documento=documento,
                producto=producto_encontrado,
                cantidad=int(detalle['cantidad']),
                vrUnitario=int(detalle['precioVenta']),
                unidad=producto_encontrado.unidadMedida.abreviatura,
                total=int(detalle['cantidad']) * int(detalle['precioVenta']),
                stockAntes=producto_encontrado.stock,
                stockDespues=producto_encontrado.stock + int(detalle['cantidad'])
            )
            producto_encontrado.stock += int(detalle['cantidad'])
            producto_encontrado.save()
            return {'message': 'Movimiento creado exitosamente.', 'success': True}
        except Exception as e:
            print(f'Error: {str(e)}')
            mensaje = {'message': 'Error en el servidor.'}
            return Response(mensaje, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def crear_movimiento_resta(self, detalle, documento):
        try:
            producto_encontrado = Producto.objects.get(id=detalle['producto_id'])
            if detalle.cantidad <= producto_encontrado.stock:
                DetalleDocumento.objects.create(
                    documento=documento,
                    producto=producto_encontrado,
                    cantidad=detalle['cantidad'],
                    unidad=producto_encontrado.unidadMedida.abreviatura,
                    vrUnitario=producto_encontrado.precioVenta,
                    total=detalle['cantidad'] * producto_encontrado.precioVenta,
                    stockAntes=producto_encontrado.stock,
                    stockDespues=producto_encontrado.stock - detalle['cantidad']
                )
                producto_encontrado.stock -= detalle['cantidad']
                producto_encontrado.save()
                return {'message': 'Movimiento creado exitosamente.', 'success': True}
            else:
                return {'message': 'El producto no tiene existencias.', 'success': False}
        except Exception as e:
            print(f'Error: {str(e)}')
            mensaje = {'message': 'Error en el servidor.'}
            return Response(mensaje, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GuardarProveedorView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            text = request.data['text']
            cleaned_json_string = self.extract_json(text)
            data = self.parse_json(cleaned_json_string)
            print(data)
            return Response({'message': '!Lo tengo!, ya esta lista tu peticion...', 'success': True,
                             'data': data}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f'Error: {str(e)}')
            mensaje = {'message': 'Error en el servidor.'}
            return Response(mensaje, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def extract_json(self, text):
        question = (f'Por favor, utiliza el siguiente texto: {text}. como base para generar un JSON con '
                    f'información de proveedor. '
                    f'El JSON debe contener con los siguientes campos: nombre, nit y telefono')
        print(question)
        client = OpenAI(api_key='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')
        response_text = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt=question,
            max_tokens=500,
            temperature=0,
        )
        cleaned_json_string = response_text.choices[0].text.strip()
        match_start = re.search(r'{', cleaned_json_string)
        match_end = re.search(r'}', cleaned_json_string[::-1])
        if match_start and match_end:
            # Calcula las posiciones de las llaves en la cadena original
            start_pos = match_start.start()
            end_pos = len(cleaned_json_string) - match_end.start()
            # Extrae la subcadena entre las llaves
            json_substring = cleaned_json_string[start_pos:end_pos]
        else:
            json_substring = {}
        return json_substring

    def parse_json(self, json_string):
        try:
            data = json.loads(json_string)
            return data
        except json.JSONDecodeError:
            raise ValueError('Error al decodificar el JSON.')


class PrecioCompraVentaViewSet(viewsets.ModelViewSet):
    queryset = PrecioCompraVenta.objects.all()
    serializer_class = PrecioCompraVentaSerializer
