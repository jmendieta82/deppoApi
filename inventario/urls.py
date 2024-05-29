from django.urls import path, include
from rest_framework.routers import DefaultRouter
from depot.views import *

router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet)
router.register(r'personas', PersonaViewSet)
router.register(r'documentos', DocumentosViewSet)
router.register(r'unidadesmedida', UnidadMedidaViewSet)
router.register(r'productos', ProductoViewSet,basename='productos')
router.register(r'proveedor', ProveedorViewSet,basename='proveedor')
router.register(r'list-productos', ListProductoViewSet,basename='list-productos')
router.register(r'movimientosinventario', DetalleMovimeintoViewSet)
router.register(r'precioscompraventa', PrecioCompraVentaViewSet)
router.register(r'detdoc_by_doc', DetalleDocuemntoByDocumentoViewSet, basename='detdoc_by_doc')
router.register(r'productos_by_name', ProductByNameViewSet,basename='productos_by_name')
router.register(r'documentos_by_empresa', DocumentosByEmpresaViewSet, basename='documentos_by_empresa')
router.register(r'move_by_product', MovesByProductViewSet, basename='move_by_product')

urlpatterns = [
    path('token', ObtainToken.as_view(), name='token'),
    path('api/', include(router.urls)),
    path('api/extract-json/', ExtractJsonView.as_view(), name='extract-json'),
    path('api/extract-json-proveedor/', ExtractJsonProveedorView.as_view(), name='extract-json-proveedor'),
    path('api/save-document/', GuardarDocumentoView.as_view(), name='save-document'),
    path('api/proveedor-fromvoice/', GuardarProveedorView.as_view(), name='proveedor-fromvoice'),
    path('api/product-voice-query/', ExtractJsonProductQueryView.as_view(), name='product-voice-query'),
]
