import requests

from django.conf import settings


class FacturaSeguraError(Exception):
    """
    Error producido al comunicarse con Factura Segura
    o cuando Factura Segura devuelve un code negativo.
    """

    def __init__(
        self,
        message,
        *,
        code=None,
        operation_id=None,
        results=None
    ):
        super().__init__(message)

        self.code = code
        self.operation_id = operation_id
        self.results = results or []


class FacturaSeguraService:
    """
    Cliente HTTP para la API ESI de Factura Segura.
    """

    ENDPOINT = '/misife00/v1/esi'

    @classmethod
    def endpoint(cls):
        base_url = settings.FACTURA_SEGURA_BASE_URL.rstrip('/')
        return f'{base_url}{cls.ENDPOINT}'

    @classmethod
    def _headers(cls):
        token = settings.FACTURA_SEGURA_TOKEN.strip()

        if not token:
            raise FacturaSeguraError(
                'No se configuró FACTURA_SEGURA_TOKEN.'
            )

        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authentication-Token': token,
        }

    @classmethod
    def _post(cls, operation, params):
        """
        Ejecuta una operación POST sobre la API ESI.
        """

        payload = {
            'operation': operation,
            'params': params,
        }

        try:
            response = requests.post(
                cls.endpoint(),
                json=payload,
                headers=cls._headers(),
                timeout=settings.FACTURA_SEGURA_TIMEOUT,
            )

        except requests.Timeout as exc:
            raise FacturaSeguraError(
                'Factura Segura no respondió dentro del tiempo esperado.'
            ) from exc

        except requests.RequestException as exc:
            raise FacturaSeguraError(
                'No se pudo establecer comunicación con Factura Segura.'
            ) from exc

        try:
            data = response.json()

        except ValueError as exc:
            raise FacturaSeguraError(
                f'Factura Segura devolvió una respuesta no JSON '
                f'(HTTP {response.status_code}).'
            ) from exc

        if not response.ok:
            raise FacturaSeguraError(
                data.get(
                    'description',
                    f'Error HTTP {response.status_code}.'
                ),
                code=data.get('code'),
                operation_id=(
                    data.get('operation_info') or {}
                ).get('id'),
                results=data.get('results', []),
            )

        code = data.get('code')

        if code is None:
            raise FacturaSeguraError(
                'La respuesta de Factura Segura no contiene code.'
            )

        operation_id = (
            data.get('operation_info') or {}
        ).get('id')

        results = data.get('results', [])

        if code < 0:
            raise FacturaSeguraError(
                data.get(
                    'description',
                    'Factura Segura rechazó la operación.'
                ),
                code=code,
                operation_id=operation_id,
                results=results,
            )

        return data

    @classmethod
    def calcular_de(cls, de_resumido):
        """
        Calcula los campos del documento electrónico sin generarlo.
        """

        return cls._post(
            operation='calcular_de',
            params={
                'DE': de_resumido
            }
        )

    @classmethod
    def generar_de(cls, de):
        """
        Genera el documento electrónico.
        """

        return cls._post(
            operation='generar_de',
            params={
                'DE': de
            }
        )

    @classmethod
    def get_estado_sifen(cls, cdc, ruc_emisor):
        """
        Consulta el estado del documento en SIFEN.
        """

        return cls._post(
            operation='get_estado_sifen',
            params={
                'CDC': cdc,
                'dRucEm': ruc_emisor,
            }
        )

    @classmethod
    def _get_archivo(cls, operation, ruc_emisor, cdc):
        url = (
            f'{cls.endpoint()}/{operation}/'
            f'{ruc_emisor}/{cdc}'
        )

        try:
            response = requests.get(
                url,
                headers=cls._headers(),
                timeout=settings.FACTURA_SEGURA_TIMEOUT,
            )

        except requests.Timeout as exc:
            raise FacturaSeguraError(
                'Tiempo de espera agotado al descargar archivo.'
            ) from exc

        except requests.RequestException as exc:
            raise FacturaSeguraError(
                f'Error de conexión con Factura Segura: {exc}'
            ) from exc

        if not response.ok:
            raise FacturaSeguraError(
                f'Error HTTP {response.status_code}: '
                f'{response.text}'
            )

        return response.content


    @classmethod
    def descargar_kude(cls, ruc_emisor, cdc):
        return cls._get_archivo(
            'dwn_kude',
            ruc_emisor,
            cdc,
        )


    @classmethod
    def descargar_xml(cls, ruc_emisor, cdc):
        return cls._get_archivo(
            'dwn_xml',
            ruc_emisor,
            cdc,
        )





